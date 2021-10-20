import xml.etree.ElementTree as ET
from argparse import ArgumentParser, RawDescriptionHelpFormatter, RawTextHelpFormatter
from math import floor
from typing import Tuple

# Global variables
yak_year_in_days = 100

def print_herd_yield(herd_yield:list,herd_results:list) -> None:
    print(f"In Stock:\n"\
        f"\t{herd_yield[0]:.3f} liters of milk\n"\
        f"\t{herd_yield[1]} skins of wool")
    formatted_str = f"Herd:\n"
    for yak in herd_results:
        formatted_str += f"\t{yak['name']} {yak['age']} years old\n"
    print(formatted_str)

def calc_herd_yield_from_xml(xml_file:str, elapsed_days:int) -> Tuple[list,list]:
    xml = get_xml_object_from_path(xml_file)
    yak_herd_list = flat_xml_to_list(xml)
    return calc_herd_yield(yak_herd_list,elapsed_days)
    
def calc_herd_yield(yak_herd_list:list, elapsed_days:int, starting_mode:bool = True) -> Tuple[list,list]:
    if starting_mode:
        total_wool = sum([1 if float(yak['age'])>=1 else 0 for yak in yak_herd_list])
    else:
        total_wool = 0
    total_milk = 0
    
    for yak in yak_herd_list:
        accum_wool = 0
        accum_milk = 0
        
        name = yak['name']
        sex = yak['sex']
        age = float(yak['age'])
        if age >= 1:
            age_last_shaved = age
        else:
            age_last_shaved = None
        
        age_days = age * 100
        for i in range(elapsed_days):
            accum_milk += 50 - (0.03 * age_days)
        
            # The last day doesn't apply as wool can only be shaved at start of day!
            prev_accum_wool = accum_wool
            if i != elapsed_days - 1:
                accum_wool += 1/(8 + 0.01 * age_days)
            age_days += 1
            
            # Get last_shaved_age
            shave_flag = floor(accum_wool) > floor(prev_accum_wool)
            if shave_flag:
                age_last_shaved = age_days / 100
        
        yak['age'] = age_days / yak_year_in_days
        yak['age-last-shaved'] = age_last_shaved
        yak['yield_wool_skins'] = floor(accum_wool)
        yak['yield_milk_litres'] = accum_milk
        total_wool += yak['yield_wool_skins']
        total_milk += yak['yield_milk_litres']

    yak_herd_yield = [total_milk,total_wool]
    yak_herd_results = yak_herd_list
    return yak_herd_yield, yak_herd_results

def flat_xml_to_list(xml_obj:ET.Element) -> list:
    assert len(list(xml_obj)) > 0, "No elements in input xml object"
    
    l = []
    [l.append(child.attrib) for child in xml_obj]
    return l

def get_xml_object_from_path(fpath:str) -> ET.Element:
    return ET.parse(fpath).getroot()

def construct_argparser() -> ArgumentParser:
    """Constructs an argument parser for flexible command line use.

    Returns
    -------
    ArgumentParser
        An argument parser object.
    """
    # Create parser object
    parser = ArgumentParser(
        description     = 'Matching results from database to SHP file.',
        formatter_class = RawTextHelpFormatter)

    # Add optional arguments
    parser.add_argument('-i', '--xml_file', type=str, required=False, default='yak.xml',
                    help="Path to XML file")
    parser.add_argument('-d', '--elapsed_days', type=int, required=False, default=13,
                    help="Number of elapsed days")
    parser.add_argument('-p', '--print_results', action='store_true', required=False,
                    help="Option to print results")
    return parser


if __name__ == '__main__':
    # Construct argparser object
    parser  = construct_argparser()
    args    = parser.parse_args()       # Parse sys.argv
    
    # Execute main
    herd_yield,herd_results = calc_herd_yield_from_xml(args.xml_file,args.elapsed_days)
    if args.print_results:
        print_herd_yield(herd_yield,herd_results)


