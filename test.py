
import psutil

def main():
    a = {}
    a['1'] = 1
    a['2'] = 1
    for k, v in a.items():
        print(k, v)

if __name__ == '__main__':
    main()