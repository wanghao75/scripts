import base64
import os
import sys

import requests
import wget


def get_recycle_repos_list_or_files(org_repo: str, src_path, dst_path):
    if os.path.exists(dst_path):
        os.remove(dst_path)

    wget.download("https://gitee.com/{}/raw/master/{}".format(org_repo, src_path), dst_path)


def get_enterprise_id(enterprise: str, v5_token: str):
    url = "https://gitee.com/api/v5/enterprises/%s?access_token=%s" % (enterprise, v5_token)
    res = requests.get(url=url)
    if res.status_code != 200:
        print("get enterprise id failed")
        sys.exit(1)
    return res.json().get("id")


def load_repos_list():
    repo_reason = {}
    with open("./recycle_repo_list.md", "r", encoding="utf-8") as f:
        data = f.readlines()

        valid_data = data[3:]

    for v in valid_data:
        repo_name, repo_url, reason = v.strip(" ").strip("").replace(" ", "").replace("\n", "").split("|")[1], \
                                      v.strip(" ").strip("").replace(" ", "").replace("\n", "").split("|")[2], \
                                      v.strip(" ").strip("").replace(" ", "").replace("\n", "").split("|")[3]
        repo_reason[repo_url] = reason
    return repo_reason


def change_repos_state(maps: dict, token: str, enterprise_id: int, status: int, ps: str):
    not_done = {}
    for k in maps:
        id_url = "https://gitee.com/api/v5/repos/{}/{}".format(k.split("/")[-2], k.split("/")[-1])
        res = requests.get(id_url)
        project_id = res.json().get("id")
        call_url = "https://api.gitee.com/enterprises/{}/projects/{}/status".format(enterprise_id, project_id)
        params = {
            "access_token": token,
            "status": status,
            "password": ps,
            "validate_type": "password"
        }

        response = requests.put(url=call_url, data=params)
        if response.status_code != 204:
            not_done[call_url] = params
            continue

    if len(not_done) != 0:
        for k, v in not_done.items():
            requests.put(url=k, data=v)


def update_repos_readme_and_description(maps: dict, token: str):
    for k in maps:
        org, repo = k.split("/")[-2], k.split("/")[-1]
        print(org, repo)
        filename = "README.md"
        en_filename = "README.en.md"

        # get file content and sha
        url1 = "https://gitee.com/api/v5/repos/{}/{}/contents/{}".format(org, repo, filename)
        params = {"access_token": token, "ref": "master"}

        res = requests.get(url=url1, params=params)

        url2 = "https://gitee.com/api/v5/repos/{}/{}/contents/{}".format(org, repo, en_filename)
        params = {"access_token": token, "ref": "master"}

        res2 = requests.get(url=url2, params=params)

        if res.status_code == 200 and len(res.json()) == 0 and res2.status_code == 200 and len(res2.json()) == 0:

            update_desc = "https://gitee.com/api/v5/repos/{}/{}".format(org, repo)
            data = {
                "access_token": token,
                "description": "仓库关闭的原因：%s" % maps[k],
                "name": repo,
            }

            requests.patch(url=update_desc, data=data)
            continue

        if len(res.json()) > 0:

            sha1 = res.json().get("sha")
            c1 = res.json().get("content")
            d1 = decode_base64_to_string(c1)

            zh_base = encode_to_base64(d1, "仓库状态设置为关闭的原因: {}\n".format(maps[k]))
            update_file_url1 = "https://gitee.com/api/v5/repos/{}/{}/contents/{}".format(org, repo, filename)
            data1 = {
                "access_token": token,
                "content": zh_base,
                "sha": sha1,
                "message": "仓库被设置为关闭的原因",
                "branch": "master"
            }

            requests.put(url=update_file_url1, data=data1)

        if len(res2.json()) > 0:
            sha2 = res2.json().get("sha")
            c2 = res2.json().get("content")
            d2 = decode_base64_to_string(c2)
            en_base = encode_to_base64(d2, "Reason why the repository's state is set to be closed: {}\n".format(maps[k]))
            update_file_url2 = "https://gitee.com/api/v5/repos/{}/{}/contents/{}".format(org, repo, en_filename)
            data2 = {
                "access_token": token,
                "content": en_base,
                "sha": sha2,
                "message": "the reason why the state of repository is set to be closed",
                "branch": "master"
            }

            requests.put(url=update_file_url2, data=data2)

        # update Description
        update_desc = "https://gitee.com/api/v5/repos/{}/{}".format(org, repo)
        data = {
            "access_token": token,
            "description": "仓库关闭的原因：%s" % maps[k],
            "name": repo,
        }

        requests.patch(url=update_desc, data=data)


def encode_to_base64(string, msg):
    l = string.split("\n")
    single = l[1]
    l[1] = msg + single

    bc = ""
    for i in l:
        bc += i + "\n"

    by = base64.b64encode(bc.encode("utf-8"))
    return by


def decode_base64_to_string(content):
    d = str(base64.b64decode(content.encode("utf-8")), "utf-8")
    return d


def clean():
    dirs = os.listdir("./")
    for d in dirs:
        if d.endswith(".md"):
            os.remove(d)


def main():
    v5_token = sys.argv[1]
    v8_token = sys.argv[2]
    enterprise = sys.argv[3]
    ci_bot_token = sys.argv[4]
    password = sys.argv[5]
    if v5_token == "" or v8_token == "" or enterprise == "" or ci_bot_token == "" or password == "":
        print("missing args")
        sys.exit(1)

    # get enterprise id
    eid = get_enterprise_id(enterprise, v5_token)

    # get data from online file
    get_recycle_repos_list_or_files("new-op/community", "sig/sig-recycle/recycle_repo_list.md", "./recycle_repo_list.md")
    data = load_repos_list()

    # change repos' state to open
    change_repos_state(data, v8_token, eid, 0, password)

    # update README file and repos' description
    update_repos_readme_and_description(data, ci_bot_token)

    # clean workspace
    clean()

    # change repo's state to close
    change_repos_state(data, v8_token, eid, 2, password)


if __name__ == '__main__':
    main()
