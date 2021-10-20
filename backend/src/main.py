import uuid
from typing import Dict, Optional

import pandas as pd
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import Herd, Order, Stock, database, engine
from xmlreader import (calc_herd_yield, calc_herd_yield_from_xml,
                       print_herd_yield)

# FastAPI with middleware configured
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define an accepted data model / structure for POST inputs
class OrderRequest(BaseModel):
    """
    Example:
    {"customer":"Medvedev","order":{"milk":1100,"skins":3}}
    """
    customer: str
    order: Dict[str, float]

# Define an accepted data model / structure for POST inputs
class ModifyHerdRequest(BaseModel):
    """
    """
    action: str
    yak_id: Optional[int]
    name: Optional[str]
    sex: Optional[str]
    age: Optional[float]

# Hardcoded
xml_file = '/assets/input_herd.xml'

# Initialise Data from XML file and temp
init_herd_yield, init_herd_results = calc_herd_yield_from_xml(xml_file,0)

# # Temp in-memory db
# db_yaks = init_herd_results
# db_yield = {'yield_milk_litres': init_herd_yield[0], 'yield_wool_skins': init_herd_yield[1]}
# db_orders = []

def execute_query(engine,q:str):
    with engine.begin() as conn:
        r = conn.execute(q)
        r.close()
    return r

def get_df_from_query(engine, query:str):
    return pd.read_sql(query, engine)

@app.get("/")
async def example() -> dict:
    print("Working")
    return {"message": "Hello World"}

@app.get("/get-db-herd")
async def get_db_herd():
    return await Herd.objects.all()

@app.get("/get-db-stock")
async def get_db_stock():
    return await Stock.objects.all()

@app.get("/get-db-order")
async def get_db_order():
    return await Order.objects.all()

@app.on_event("startup")
async def startup():
    if not database.is_connected:
        await database.connect()

    # Reset database
    q = 'DELETE FROM public.herd'
    execute_query(engine,q)
    q = 'DELETE FROM public.stock'
    execute_query(engine,q)
    q = 'DELETE FROM public.order'
    execute_query(engine,q)

    # Initialise Herd table
    for yak in init_herd_results:
        # get_or_create is another method
        await Herd.objects.create(
            name = yak['name'],
            sex = yak['sex'],
            age = yak['age'],
            age_last_shaved = yak['age-last-shaved'],
            yield_milk_litres = yak['yield_milk_litres'],
            yield_wool_skins = yak['yield_wool_skins']
        )
    # Initialise Stock table
    await Stock.objects.create(
        yield_milk_litres = init_herd_yield[0],
        yield_wool_skins = init_herd_yield[1]
    )

@app.on_event("shutdown")
async def shutdown():
    if database.is_connected:
        await database.disconnect()

@app.get("/yak-shop/stock/{elapsed_days}")
async def get_stock_info(elapsed_days:int,print_results:bool=True) -> dict:
    print(f"Inputted number of elapsed days: {elapsed_days} days")

    q = 'SELECT * FROM public.herd'
    db_yaks = get_df_from_query(engine,q).to_dict('records')
    q = 'SELECT * FROM public.stock'
    db_yield = get_df_from_query(engine,q).to_dict('records')[0]

    herd_yield, herd_results = calc_herd_yield(db_yaks,elapsed_days,starting_mode=False)
    herd_yield[0] += db_yield['yield_milk_litres']
    herd_yield[1] += db_yield['yield_wool_skins']
    if print_results:
        print_herd_yield(herd_yield,herd_results)
    return {'milk':herd_yield[0],'skins':herd_yield[1]}

@app.get("/yak-shop/herd/{elapsed_days}")
async def get_herd_info(elapsed_days:int,print_results:bool=True) -> dict:
    print(f"Inputted number of elapsed days: {elapsed_days} days")
    
    q = 'SELECT * FROM public.herd'
    db_yaks = get_df_from_query(engine,q).to_dict('records')
    q = 'SELECT * FROM public.stock'
    db_yield = get_df_from_query(engine,q).to_dict('records')[0]

    herd_yield, herd_results = calc_herd_yield(db_yaks,elapsed_days,starting_mode=False)
    herd_yield[0] += db_yield['yield_milk_litres']
    herd_yield[1] += db_yield['yield_wool_skins']
    if print_results:
        print_herd_yield(herd_yield,herd_results)
    response_list = []
    for yak in herd_results:
        response_list.append({'name':yak['name'],'age':yak['age'],'age-last-shaved':yak['age-last-shaved']})
    return {'herd':response_list}

@app.post("/yak-shop/modify/herd")
async def modify_initial_herd(modify_herd:ModifyHerdRequest) -> None:
    print(f"Request received to modify herd")

    # Get results and check input
    modify_herd_dict = modify_herd.dict()
    assert modify_herd_dict['action'] in ['add','remove'], \
        f"ERROR: {modify_herd_dict['action']} is not an allowable action! - Allowed inputs (['add','remove'])"

    if modify_herd_dict['action'] == 'remove':
        q = f"DELETE FROM public.herd WHERE yak_id = {modify_herd_dict['yak_id']}"
        execute_query(engine,q)
    elif modify_herd_dict['action'] == 'add':
        yak = {}
        yak['name'] = modify_herd_dict['name']
        yak['sex'] = modify_herd_dict['sex']
        yak['age'] = modify_herd_dict['age']
        yak['age-last-shaved'] = [yak['age'] if yak['age']>=1 else 0][0]
        yak['yield_milk_litres'] = 0
        yak['yield_wool_skins'] = 0     # Shaved on the first day irregardless!
        await Herd.objects.create(
            name = yak['name'],
            sex = yak['sex'],
            age = yak['age'],
            age_last_shaved = yak['age-last-shaved'],
            yield_milk_litres = yak['yield_milk_litres'],
            yield_wool_skins = yak['yield_wool_skins']
        )

    # Recalculate initial yield!
    q = 'SELECT * FROM public.herd'
    db_yaks = get_df_from_query(engine,q).to_dict('records')
    herd_yield, _ = calc_herd_yield(db_yaks,0,starting_mode=True)
    q = 'DELETE FROM public.stock'
    execute_query(engine,q)
    await Stock.objects.create(
        yield_milk_litres = herd_yield[0],
        yield_wool_skins = herd_yield[1]
    )
    return

# @app.post("/yak-shop/donate/day")
# @app.post("/yak-shop/kill/day")

@app.post("/yak-shop/order/{order_day}", status_code=status.HTTP_201_CREATED)
async def place_order(order_day:int,order:OrderRequest, response:Response) -> dict:
    print(f"Day number when order is placed: {order_day} day")

    q = 'SELECT * FROM public.herd'
    db_yaks = get_df_from_query(engine,q).to_dict('records')
    q = 'SELECT * FROM public.stock'
    db_yield = get_df_from_query(engine,q).to_dict('records')[0]
    q = 'SELECT * FROM public.order'
    db_orders = get_df_from_query(engine,q).to_dict('records')
    print("DB orders list - ",db_orders)
    print(f"There are {len(db_orders)} existing orders in the orders DB for days {[db_order['order_day'] for db_order in db_orders]}")

    # Create new order 
    order_requested = order.dict()
    current_order_id = str(uuid.uuid4())
    order_requested['order_id'] = current_order_id
    order_requested['order_day'] = order_day
    order_requested['requested_milk'] = order_requested['order']['milk']
    order_requested['requested_wool'] = order_requested['order']['skins']
    order_requested.pop('order',None)

    # Upload order request to db
    await Order.objects.create(
        order_id = current_order_id,
        order_day = order_day,
        customer = order_requested['customer'],
        requested_milk = order_requested['requested_milk'],
        requested_wool = order_requested['requested_wool']
    )

    # Append order and sort by day (ASCENDING)
    db_orders.append(order_requested)
    db_orders = sorted(db_orders, key = lambda x:x['order_day'], reverse=False)

    # Calculate for each order in ascending fashion
    for ind, order_dict in enumerate(db_orders,0):
        print(f"Processing order {ind}/{len(db_orders)}: {order_dict}")

        # Get elapsed days and the herd results for the day the order is placed
        if ind == 0:
            elapsed_days = order_dict['order_day']
        else:
            elapsed_days = order_dict['order_day'] - db_orders[ind-1]['order_day']
        herd_yield, db_yaks = calc_herd_yield(db_yaks, elapsed_days,starting_mode=False)

        # Save / add in yield results for elapsed days
        db_yield['yield_wool_skins'] += herd_yield[1]
        db_yield['yield_milk_litres'] += herd_yield[0]

        # Subtract milk order
        if order_dict['requested_milk'] > db_yield['yield_milk_litres']:
            print(f"Day {order_dict['order_day']} order ({order_dict['order_id']}) UNSUCCESSFUL for milk!")
            # Update local yield + order 
            db_orders[ind]['received_milk'] = 0
        else:
            print(f"Day {order_dict['order_day']} order ({order_dict['order_id']}) placed successfully for milk!")
            # Update local yield + order 
            db_yield['yield_milk_litres'] -= order_dict['requested_milk']
            db_orders[ind]['received_milk'] = order_dict['requested_milk']
        # Update database order for received
        order_db_entry = await Order.objects.get(order_id=order_dict['order_id'])
        assert order_db_entry.order_id == order_dict['order_id']
        order_db_entry.received_milk = db_orders[ind]['received_milk']
        await order_db_entry.update()

        # Subtract wool order
        if order_dict['requested_wool'] > db_yield['yield_wool_skins']:
            print(f"Day {order_dict['order_day']} order ({order_dict['order_id']}) UNSUCCESSFUL for wool!")
            # Update local yield + order 
            db_orders[ind]['received_wool'] = 0
        else:
            print(f"Day {order_dict['order_day']} order ({order_dict['order_id']}) placed successfully for wool!")
            # Update local yield + order 
            db_yield['yield_wool_skins'] -= order_dict['requested_wool']
            db_orders[ind]['received_wool'] = order_dict['requested_wool']
        # Update database order for received
        order_db_entry = await Order.objects.get(order_id=order_dict['order_id'])
        assert order_db_entry.order_id == order_dict['order_id']
        order_db_entry.received_wool = db_orders[ind]['received_wool']
        await order_db_entry.update()

    # Return the current order
    current_order = list(filter(lambda order:order['order_id'] == current_order_id, db_orders))[0]
    current_order_received = {}

    # Prepare return response
    if current_order['received_milk']:  current_order_received['milk'] = current_order['received_milk']
    if current_order['received_wool']:  current_order_received['skins'] = current_order['received_wool']
    
    # Process return status codes based on results
    milk_flag = 'milk' in current_order_received.keys()
    wool_flag = 'skins' in current_order_received.keys()
    if all([milk_flag, wool_flag]):         response.status_code = status.HTTP_201_CREATED
    elif sum([milk_flag, wool_flag]) == 0:  response.status_code = status.HTTP_404_NOT_FOUND
    elif sum([milk_flag, wool_flag]) == 1:  response.status_code = status.HTTP_206_PARTIAL_CONTENT
    else:
        print(f"ERROR: Unexpected error occured when calculating flags - {[milk_flag, wool_flag]}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    max_order_day = max([o['order_day'] for o in db_orders])
    print(f"Finished processing orders. Final results - {db_orders}. Current order id = {current_order_id}")
    print(f"Stock on most recent order day ({max_order_day}) - {db_yield}\n\n")
    return current_order_received

# @app.post("/data")
# async def data(request: Request):
#     content = await request.json()
#     print("Received:")
#     print(content)
#     print(request.headers)
#     return True


