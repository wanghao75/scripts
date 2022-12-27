import csv
import datetime
import os
import sys
import time

import requests


def get_enterprise_id(enterprise: str, v5_token: str):
    url = "https://gitee.com/api/v5/enterprises/%s?access_token=%s" % (enterprise, v5_token)
    res = requests.get(url=url)
    if res.status_code != 200:
        print("get enterprise id failed")
        sys.exit(1)
    return res.json().get("id")


def get_all_enterprise_members_by_id(enterprise_name: str, v5_token: str):
    page = 1
    user_ids = []
    while True:
        retry = 0
        url_add = "https://gitee.com/api/v5/enterprises/{}/members".format(enterprise_name)
        params = {
            "access_token": v5_token,
            "page": page,
            "per_page": 100,
        }

        res = requests.get(url=url_add, params=params)

        if res.status_code != 200:
            if retry < 2:
                retry += 1
                continue
            else:
                print("call gitee api failed")
                break

        if len(res.json()) == 0:
            break

        for r in res.json():
            user_ids.append(r.get("user").get("id"))
        page += 1
    return user_ids


def check_members_activity(enterprise_id: int, user_ids: list, v8_token: str):
    print("start check ", datetime.datetime.now())
    not_activate_members = {}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64)", "Connection": "close"}
    not_check = {}
    for uid in user_ids:
        time.sleep(1)
        check_url = "https://api.gitee.com/enterprises/%d/members/%d/events" % (enterprise_id, uid)
        params = {
            "access_token": v8_token,
            "limit": 300
        }

        response = requests.get(url=check_url, params=params, headers=headers)
        if response.status_code != 200:
            not_check[check_url] = {"id": uid, "para": params}
            print(response.status_code)
            continue

        # 在时间范围内未存在有贡献记录
        if len(response.json().get("data")) == 0:
            with open("./no_data_members.txt", "a", encoding="utf-8") as f:
                f.writelines(str(uid) + "\n")
            not_activate_members[uid] = "never contributed"
            continue

        # 获取所有成员
        for work in response.json().get("data"):
            if work.get("action") in ["kick_out", "left", "be_left"]:
                not_activate_members[uid] = "never contributed"
            else:
                last_work = work
                not_activate_members[uid] = last_work.get("created_at")
                break

        time.sleep(1)
        if not_activate_members[uid] == "never contributed":

            req = requests.get(url=check_url, params=params, headers=headers)

            if req.status_code != 200:
                print("91 status code ", req.status_code)
                not_check[check_url] = {"id": uid, "para": params}
                continue

            if len(req.json().get("data")) == 0:
                continue

            for w in req.json().get("data"):
                if w.get("action") in ["kick_out", "left", "be_left"]:
                    not_activate_members[uid] = "never contributed"
                else:
                    last_work = w
                    not_activate_members[uid] = last_work.get("created_at")
                    break

    if len(not_check) != 0:
        print("get in not check")
        for k, v in not_check.items():
            time.sleep(1)
            response = requests.get(url=k, params=v.get("para"), headers=headers)
            if response.status_code != 200:
                print(response.status_code)
                continue

            # 在时间范围内未存在有贡献记录
            if len(response.json().get("data")) == 0:
                not_activate_members[v.get("id")] = "never contributed"
                continue

            # 获取所有成员
            for work in response.json().get("data"):
                if work.get("action") in ["kick_out", "left", "be_left"]:
                    not_activate_members[v.get("id")] = "never contributed"
                else:
                    last_work = work
                    not_activate_members[v.get("id")] = last_work.get("created_at")
                    break

            time.sleep(1)
            if not_activate_members[v.get("id")] == "never contributed":
                req = requests.get(url=k, params=v.get("para"), headers=headers)

                if req.status_code != 200:
                    print("137 status code ", req.status_code)
                    continue

                if len(req.json().get("data")) == 0:
                    with open("./no_data_members.txt", "a", encoding="utf-8") as f:
                        f.writelines(str(v.get("id")) + "\n")
                    continue

                for w in req.json().get("data"):
                    if w.get("action") in ["kick_out", "left", "be_left"]:
                        not_activate_members[v.get("id")] = "never contributed"
                    else:
                        last_work = w
                        not_activate_members[v.get("id")] = last_work.get("created_at")
                        break

    return enterprise_id, not_activate_members


def write():
    if os.path.exists("./remove_list.txt"):
        os.remove("./remove_list.txt")
    with open("./members_to_remove_new.csv", "r", encoding="utf-8") as f:
        data = f.readlines()[1:]

        with open("./remove_list.txt", "a", encoding="utf-8") as ff:
            for d in data:
                if int(d.split(",")[-1]) >= 365:
                    ff.writelines(d)


def check_data(token, ps):
    with open("./remove_list.txt", "r", encoding="utf-8") as f:
        d = f.readlines()
        for i in d:
            uri = "https://api.gitee.com/enterprises/5292411/members/%s/events" % i.split(",")[2]
            p = {"access_token": token, "limit": 300}
            res = requests.get(url=uri, params=p)

            if res.status_code != 200:
                print("code is ", res.status_code)
                continue

            for r in res.json().get("data"):
                if r.get("action") not in ["kick_out", "left", "be_left"]:
                    if r.get("created_at").split("T")[0] == i.split(",")[4]:
                        remove(token, ps, i.split(",")[2])
                        break
                    else:
                        print("record time not match last work time ", i.split(",")[2], i.split(",")[4], r.get("created_at"))
                        break


def remove(token, ps, uid):
    remove_url = "https://api.gitee.com/enterprises/5292411/members/%s" % uid
    res = requests.delete(url=remove_url, params={"access_token": token, "password": ps})
    if res.status_code != 204:
        requests.delete(url=remove_url, params={"access_token": token, "password": ps})


def get_needed_to_remove_enterprise_member_information(eid: int, not_work_members_ids_dict: dict, v8_token: str):
    print("start get information ", datetime.datetime.now())
    information = []
    for nt in not_work_members_ids_dict:
        info_url = "https://api.gitee.com/enterprises/%d/members/%d" % (eid, nt)
        params = {
            "access_token": v8_token,
        }

        res = requests.get(url=info_url, params=params)
        if res.status_code != 200:
            print(res.status_code)
            continue

        login = res.json().get("user").get("login")
        name = res.json().get("user").get("name")
        join_time = res.json().get("created_at")
        member_id = nt
        if not_work_members_ids_dict[nt] == "never contributed":
            last_work = join_time.split("T")[0]
        else:
            last_work = not_work_members_ids_dict[nt].split("T")[0]

        # 计算从最后一次贡献到当前的时间间隔
        join_year, join_mon, join_day = int(join_time.split("T")[0].split("-")[0]), \
                                        int(join_time.split("T")[0].split("-")[1]), \
                                        int(join_time.split("T")[0].split("-")[2])
        last_year, last_month, last_day = last_work.split("-")[0], \
                                          last_work.split("-")[1], \
                                          last_work.split("-")[2]

        if datetime.date(join_year, join_mon, join_day) > datetime.date(int(last_year), int(last_month), int(last_day)):
            time_stamp = datetime.date.today() - datetime.date(int(join_year), int(join_mon), int(join_day))
        else:
            time_stamp = datetime.date.today() - datetime.date(int(last_year), int(last_month), int(last_day))
        days = time_stamp.days

        info = []
        info.append(name)
        info.append(login)
        info.append(member_id)
        info.append(join_time)
        info.append(last_work)
        info.append(days)
        information.append(info)

    print("end get information ", datetime.datetime.now())
    return information


def write_member_to_csv(information_lists: list):
    if os.path.exists("./members_to_remove_new.csv"):
        os.remove("./members_to_remove_new.csv")
    with open("./members_to_remove_new.csv", "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["成员名称", "成员giteeid", "企业成员id", "加入企业时间", "最后贡献时间", "时间间隔"])
        writer.writerows(information_lists)


def main():
    v5_token = sys.argv[1]
    enterprise = sys.argv[2]
    password = sys.argv[3]
    v8_token = sys.argv[4]
    #
    # res = requests.get(url="")
    # v8_token = res.json().get("access_token")

    if v5_token == "" or v8_token == "" or enterprise == "" or password == "":
        print("missing args")
        sys.exit(1)

    # get enterprise id
    eid = get_enterprise_id(enterprise, v5_token)

    user_ids = get_all_enterprise_members_by_id(enterprise, v5_token)

    enter_id, not_work_members_id = check_members_activity(eid, user_ids, v8_token)
    inf = get_needed_to_remove_enterprise_member_information(enter_id, not_work_members_id, v8_token)
    write_member_to_csv(inf)

    write()
    check_data(v8_token, password)


if __name__ == '__main__':
    main()
