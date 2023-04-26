import datetime


with open("/home/patches/patch2pr.log", "r", encoding="utf-8") as f1:
    data = f1.readlines()
    with open("/home/patches/log.log", "a", encoding="utf-8") as f2:
        f2.writelines("\n******************************************\n")
        f2.writelines("\nlog time {}\n\n".format(datetime.datetime.now()))
        for d in data:
            f2.writelines(d)
        f2.writelines("\n******************************************\n")
