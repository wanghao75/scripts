import os
import smtplib
import sys
from email.mime.text import MIMEText

import requests


def get_pr_changed_files(o, r, n, t, gh_t):
    if o == "opengauss":
        get_url = "https://gitee.com/api/v5/repos/{}/{}/pulls/{}/files".format(o, r, n)
        params = {
            "access_token": t
        }

        files = []
        community = ""
        pr_link = "https://gitee.com/{}/{}/pulls/{}".format(o, r, n)

        res = requests.get(url=get_url, params=params)
        if res.status_code != 200:
            print("can't get pr's files")
            sys.exit(1)

        for r in res.json():
            if r.get("status") != "added":
                continue
            else:
                files.append(r.get("filename"))
                community = r.get("blob_url").split("/blob/")[0]

        if len(files) > 0:
            return files, community, pr_link
        else:
            print("this pr is not creating a new service folder, never mind")
            return [], "", ""

    else:
        files = []
        community = ""
        pr_link = "https://github.com/{}/{}/pulls/{}".format(o, r, n)

        get_file_url = "https://api.github.com/repos/{}/{}/pulls/{}/files".format(o, r, n)
        headers = {
            "Authorization": "token: %s" % gh_t
        }
        res = requests.get(url=get_file_url, headers=headers)

        if res.status_code != 200:
            print("can't get pr's files")
            sys.exit(1)

        for r in res.json():
            if r.get("status") != "added":
                continue
            else:
                files.append(r.get("filename"))
                community = r.get("blob_url").split("/blob/")[0]

        if len(files) > 0:
            return files, community, pr_link
        else:
            print("this pr is not creating a new service folder, never mind")
            return [], "", ""


def check_if_files_are_newly(file_list, comm):
    if os.path.exists(comm.split("/")[-1]):
        os.remove(comm.split("/")[-1])
    os.system("git clone %s" % comm)
    flag_of_send_email = False
    if comm.__contains__("opengauss"):
        folders = os.listdir(comm.split("/")[-1] + "/deploy")
    else:
        folders = os.listdir(comm.split("/")[-1] + "/applications")
    for f in file_list:
        if f.split("applications/")[1].split("/")[0] in folders:
            flag_of_send_email = True
        else:
            flag_of_send_email = False

    return flag_of_send_email


def get_template(pr_str):
    body = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <title>Log</title>
    </head>

    <body leftmargin="8" marginwidth="0" topmargin="8" marginheight="4">
        <table width="95%" cellpadding="0" cellspacing="0"  style="font-size: 11pt; font-family: Tahoma, Arial, Helvetica, sans-serif">
            <tr>
                This email is sent automatically, no need to reply!<br>
                <br>
            </tr>
            <tr>
                new service deploy files has been merged, pull request link: {}
            </tr>
            <tr>
                <td>
                <hr size="2" width="100%" align="center" /></td>
            </tr>
        </table>
    </body>
    </html>
    """.format(pr_str)
    return body


def send_email(smtp_pass, pr):

    html_body = get_template(pr)
    msg = MIMEText(html_body, 'html', 'utf-8')
    msg['From'] = 'noReply<{}>'.format("shalldows@163.com")
    receivers = "wanghaosqsq@163.com,"
    msg['To'] = receivers
    msg['Subject'] = 'new service folder has been created, please register on argocd'
    try:
        server = smtplib.SMTP("smtp.163.com", "25")
        server.ehlo()
        server.starttls()
        server.login("shalldows@163.com", smtp_pass)
        print('login success')
        server.sendmail("shalldows@163.com", receivers.split(','), msg.as_string())
        print('send email successfully')
    except TimeoutError as e:
        print('time out', e)
        sys.exit(1)


def get_pr_link_by_commit_message(t: str):
    headers = {
        "Authorization": "token: %s" % t
    }
    repo_urls, commit = get_repo_url_by_env()
    pr = ""
    for r in repo_urls:
        r = r.replace("\n", "")
        o = r.split("/")[-2]
        rp = r.split("/")[-1]
        url1 = "https://api.github.com/repos/{}/{}/commits".format(o, rp)
        res = requests.get(url=url1, headers=headers)
        if res.status_code != 200:
            res = requests.get(url=url1, headers=headers)
        if res.json()[0].get("sha") == commit.replace("\n", ""):
            url2 = "https://api.github.com/repos/{}/{}/commits/{}/pulls".format(o, rp, res.json()[0].get("sha"))
            res2 = requests.get(url=url2, headers=headers)
            if res2.status_code != 200:
                res2 = requests.get(url=url2, headers=headers)
            pr = res2.json()[0].get("url")

        else:
            continue
    return pr


def get_repo_url_by_env():
    envs = os.popen("env").readlines()
    commit = ""
    repo_urls = []
    for e in envs:
        if e.startswith("GIT_URL_"):
            repo_urls.append(e.split("=")[1])
        if e.startswith("GIT_COMMIT"):
            commit = e.split("=")[-1]
        else:
            continue

    return repo_urls, commit


def main():
    smtp_password = sys.argv[1]
    token = sys.argv[2]
    gh_token = sys.argv[3]
    if len(sys.argv) != 4:
        sys.exit(1)

    pr_link = get_pr_link_by_commit_message(gh_token)
    org = pr_link.split("/")[-4]
    repo = pr_link.split("/")[-3]
    number = pr_link.split("/")[-1]

    fs, co, pr_l = get_pr_changed_files(org, repo, number, token, gh_token)
    if len(fs) < 0 or co == "" or pr_l == "":
        sys.exit(1)

    send = check_if_files_are_newly(fs, co)
    if send:
        send_email(smtp_password, pr_l)


if __name__ == '__main__':
    main()
