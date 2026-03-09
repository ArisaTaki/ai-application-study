from app.chat.engine import Engine

def main():
    engine = Engine()
 
    result = engine.chat(
         "我最近很烦躁，被项目客户一而再再而三地修改，而且不加工期不给商量。",
         history = "用户之前提到正在做一个很麻烦的项目，没有设计，客户无理取闹。",
         long_term_memory = "用户希望能够尽快结束这个项目，并且有更多的时间学习脱离传统开发的行业。"
     )
   
    print(result)
    

if __name__ == "__main__":
    main()
