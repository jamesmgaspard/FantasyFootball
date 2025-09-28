item = input ("What item would you like to buy?:" )
price = input ("What is the price of the item?:")
quantity = input ("How many would you like to buy?:" )
total = float(price) * int(quantity)

print (f"Your total for {quantity} {item}/s is ${total:.2f}.")