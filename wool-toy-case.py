
wool = 0
age = 400
cnt = 0

for i in range(0,12):
    wool += 1/(8 + 0.01*age)
    age += 1
    cnt += 1
    
print(cnt, wool)
