COUNT = 30

def fibo_rec(num1: int, num2: int, counter: int) -> None:
    if counter == 0:
        counter = print_fibo(counter, num1)
        counter = print_fibo(counter, num2)
    num3 = num1 + num2
    counter = print_fibo(counter, num3)
    if counter >= COUNT:
        return
    fibo_rec(num2, num3, counter)


def print_fibo(counter: int, value: int) -> int:
    counter += 1
    print(str(counter) + ":" + str(value))
    return counter

counter = 0
fibo_rec(1, 2, counter)


def fibo():
    num1 = 1
    num2 = 2
    counter = 1
    counter = print_fibo(counter, num1)
    counter = print_fibo(counter, num2)
    for _ in range(COUNT - 2):
        num3 = num1 + num2
        counter = print_fibo(counter, num3)
        num1 = num2
        num2 = num3



# fibo()