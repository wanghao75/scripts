import logging
import time
import requests
import os

BRANCHES_MAP = {
    "master": "master",
    "openEuler-1.0-LTS": "openEuler-1.0-LTS",
    "openEuler-22.03-LTS-SP1": "openEuler-22.03-LTS-SP1",
    "OLK-5.10": "OLK-5.10",
    "openEuler-22.03-LTS": "openEuler-22.03-LTS",
    "openEuler-22.09": "openEuler-22.09",
    "devel-6.1": "devel-6.1",
    "openEuler-22.03-LTS-Ascend": "openEuler-22.03-LTS-Ascend",
    "openEuler-22.09-HCK": "openEuler-22.09-HCK",
    "openEuler-20.03-LTS-SP3": "openEuler-20.03-LTS-SP3",
    "openEuler-21.09": "openEuler-21.09",
    "openEuler-21.03": "openEuler-21.03",
    "openEuler-20.09": "openEuler-20.09",
}


def make_fork_same_with_origin(branch_name):
    remotes = os.popen("git remote -v").readlines()
    remote_flag = False
    for remote in remotes:
        if remote.startswith("upstream "):
            remote_flag = False
            continue
        else:
            remote_flag = True

    if remote_flag:
        os.popen("git remote add upstream https://gitee.com/new-op/kernel.git")
    else:
        os.popen("git checkout {}".format(branch_name)).readlines()
        os.popen("git pull upstream {}".format(branch_name)).readlines()


def get_mail_step():
    if os.path.exists("/home/patches/project_series.txt"):
        os.remove("/home/patches/project_series.txt")
    os.popen('getmail --getmaildir="/home/patches/" --idle INBOX').readlines()


def download_patches_by_using_git_pw(ser_id):
    # os.popen("rm -rf /home/patches/*")
    if not os.path.exists("/home/patches/{}".format(ser_id)):
        os.popen("mkdir -p /home/patches/{}".format(ser_id))
    res = os.popen("git-pw series download {} /home/patches/{}/".format(ser_id, ser_id)).readlines()
    for r in res:
        if "Failed" in r:
            os.popen("git-pw series download {} /home/patches/{}/".format(ser_id, ser_id)).readlines()


def get_project_and_series_information():
    if not os.path.exists("/home/patches/project_series.txt"):
        return []
    with open("/home/patches/project_series.txt", "r", encoding="utf-8") as f:
        infor = f.readlines()

    return infor


def config_git():
    os.popen("git config --global user.email {};git config --global user.name {}".format(os.getenv("CI_BOT_EMAIL"),
                                                                                         os.getenv("CI_BOT_NAME")))


def config_get_mail(u_name, u_pass, email_server, path_of_sh):
    if os.path.exists("/home/patches/getmailrc"):
        with open("/home/patches/getmailrc", "r", encoding="utf-8") as ff:
            content = ff.readlines()
            if len(content) == 0:
                os.popen("rm -f /home/patches/getmailrc").readlines()
                os.popen("touch /home/patches/getmailrc").readlines()
            else:
                return
    else:
        os.popen("touch /home/patches/getmailrc").readlines()

    retriever = ["[retriever]", "type = SimplePOP3SSLRetriever",
                 "server = {}".format(email_server), "username = {}".format(u_name), "password = {}".format(u_pass),
                 "port = {}".format(os.getenv("EMAIL_PORT"))
                 ]

    destination = ["[destination]", "type = MDA_external", "path = {}".format(path_of_sh), "ignore_stderr = true"]

    options = ["[options]", "delete = false", "message_log = /home/patches/getmail.log",
               "message_log_verbose = true", "read_all = false", "received = false", "delivered_to = false"]

    with open("/home/patches/getmailrc", "a", encoding="utf-8") as f:
        f.writelines([r + "\n" for r in retriever])
        f.writelines([r + "\n" for r in destination])
        f.writelines([r + "\n" for r in options])


def config_git_pw(project_name, server_link, token):
    os.popen("git config --global pw.server {};git config --global pw.token {};git config --global pw.project {}"
             .format(server_link, token, project_name))


# if use the patchwork, we can make it by the following codes
# use patches
def make_branch_and_apply_patch(user, token, origin_branch, ser_id):
    if not os.path.exists("/home/patches/kernel"):
        os.chdir("/home/patches")
        r = os.popen("git clone https://{}:{}@gitee.com/patch-bot/kernel.git".format(user, token)).readlines()
        for res in r:
            if "error:" in res or "fatal:" in res:
                os.popen("git clone https://{}:{}@gitee.com/patch-bot/kernel.git".format(user, token)).readlines()
        os.chdir("/home/patches/kernel")
        make_fork_same_with_origin(origin_branch)
    else:
        os.chdir("/home/patches/kernel")
        make_fork_same_with_origin(origin_branch)

    # delete all branches startswith patch
    # branches_list = os.popen("git branch").readlines()
    # for b in branches_list:
    #     if b.startswith("patch-"):
    #         os.popen("git branch -D %s" % b).readlines()

    new_branch = "patch-%s" % int(time.time())
    os.popen("git checkout -b %s origin/%s" % (new_branch, origin_branch)).readlines()

    # git am
    patches_dir = "/home/patches/{}/".format(ser_id)
    am_res = os.popen("git am --abort;git am %s*.patch" % patches_dir).readlines()
    am_success = False
    for am_r in am_res:
        if am_r.__contains__("Patch failed at"):
            am_success = False
            logging.error("failed to apply patch, reason is %s" % am_r)
            break
        else:
            am_success = True

    if am_success:
        os.popen("git push origin %s" % new_branch).readlines()
        return new_branch


# summit a pr
def make_pr_to_summit_commit(source_branch, base_branch, token, pr_url_in_email_list, cover_letter, receiver_email):
    title = "[patch-sync] create pr from patches"
    if pr_url_in_email_list or cover_letter:
        body = "PR sync from: \n{} \n{}".format(pr_url_in_email_list, cover_letter)
    else:
        body = ""

    data = {
        "access_token": token,
        "head": "patch-bot:" + source_branch,
        "base": base_branch,
        "title": title,
        "body": body,
        "prune_source_branch": "true"
    }
    res = requests.post(url="https://gitee.com/api/v5/repos/new-op/kernel/pulls", data=data)

    if res.status_code == 201:
        pull_link = res.json().get("url")
        send_mail_to_notice_developers(pull_link, receiver_email)


# use email to notice that pr has been created
def send_mail_to_notice_developers(pr, email_address):
    import smtplib
    from email.mime.text import MIMEText

    mail_host = os.getenv("SEND_EMAIL_HOST", "")
    mail_user = os.getenv("SEND_EMAIL_HOST_USER", "")
    mail_pass = os.getenv("SEND_EMAIL_HOST_PASSWORD", "")
    sender = mail_user
    receivers = ",".join(email_address)

    content = "your patch has been converted to a pull request, pull request link is: %s" % pr
    title = "notice"
    message = MIMEText(content, 'plain', 'utf-8')
    message['From'] = "patchwork bot <{}>".format(sender)
    message['To'] = receivers
    message['Subject'] = title

    try:
        smtpObj = smtplib.SMTP(mail_host, os.getenv("SEND_EMAIL_PORT", 25))
        smtpObj.ehlo()
        smtpObj.starttls()
        smtpObj.login(mail_user, mail_pass)
        smtpObj.sendmail(sender, receivers.split(","), message.as_string())
        smtpObj.quit()
    except smtplib.SMTPException as e:
        import logging
        logging.info("send mail failed, ", e)


def get_email_content_sender_and_covert_to_pr_body(ser_id):
    import psycopg2
    user = os.getenv("DATABASE_USER")
    name = os.getenv("DATABASE_NAME")
    password = os.getenv("DATABASE_PASSWORD")
    host = os.getenv("DATABASE_HOST")

    conn = psycopg2.connect(database=name, user=user, password=password, host=host, port="5432")

    cur = conn.cursor()

    cur.execute("SELECT * from patchwork_series where id={}".format(ser_id))
    series_rows = cur.fetchall()
    cover_letter_id = 0
    for row in series_rows:
        cover_letter_id = row[-1]

    # no cover
    patch_sender_email = ""
    body = ""
    email_list_link_of_patch = ""

    if cover_letter_id is None or cover_letter_id == 0:
        cur.execute("SELECT name from patchwork_patch where series_id={}".format(ser_id))
        patches_names_rows = cur.fetchall()
        first_path_mail_name = ""
        if len(patches_names_rows) == 1:
            first_path_mail_name = patches_names_rows[0][0]
        else:
            for row in patches_names_rows:
                if row[0].__contains__("01/") or row[0].__contains__("1/"):
                    first_path_mail_name = row[0]

        cur.execute(
            "SELECT headers from patchwork_patch where series_id={} and name='{}'".format(ser_id, first_path_mail_name))
        patches_headers_rows = cur.fetchall()
        for row in patches_headers_rows:
            for string in row[0].split("\n"):
                who_is_email_list = ""
                if string.startswith("To: "):
                    if "<" in string:
                        who_is_email_list = string.split("<")[1].split(">")[0]
                    else:
                        who_is_email_list = string.split(" ")[1]
                if string.startswith("From: "):
                    patch_sender_email = string.split("<")[1].split(">")[0]
                if string.__contains__("https://mailweb.openeuler.org/hyperkitty/list/%s/message/" % who_is_email_list):
                    email_list_link_of_patch = string.replace("<", "").replace(">", "").replace("message", "thread")

        return patch_sender_email, body, email_list_link_of_patch

    cur.execute("SELECT * from patchwork_cover where id={}".format(cover_letter_id))
    cover_rows = cur.fetchall()
    cover_headers = ""
    cover_content = ""
    for row in cover_rows:
        cover_headers = row[3]
        cover_content = row[4]

    if cover_content == "" or cover_headers == "":
        return "", "", ""

    cover_who_is_email_list = ""
    for ch in cover_headers.split("\n"):
        if ch.startswith("To: "):
            if "<" in ch:
                cover_who_is_email_list = ch.split("<")[1].split(">")[0]
            else:
                cover_who_is_email_list = ch.split(" ")[1]
        if ch.__contains__("https://mailweb.openeuler.org/hyperkitty/list/%s/message/" % cover_who_is_email_list):
            email_list_link_of_patch = ch.replace("<", "").replace(">", "").replace("message", "thread")
        if ch.startswith("From: "):
            patch_sender_email = ch.split("From: ")[1].split("<")[1].split(">")[0]

    for ct in cover_content.split("\n"):
        if ct.__contains__("(+)") or ct.__contains__("(-)") or "mode" in ct or "| " in ct:
            continue
        else:
            body += ct + "\n"

    return patch_sender_email, body, email_list_link_of_patch


def main():
    server = os.getenv("PATCHWORK_SERVER", "")
    server_token = os.getenv("PATCHWORK_TOKEN", "")
    repo_user = os.getenv("REPO_OWNER", "")
    gitee_token = os.getenv("GITEE_TOKEN", "")
    not_cibot_gitee_token = os.getenv("GITEE_TOKEN_NOT_CI_BOT", "")
    user_email = os.getenv("EMAIL_HOST_USER", "")
    user_pass = os.getenv("EMAIL_HOST_PASSWORD", "")
    mail_server = os.getenv("EMAIL_HOST", "")

    if server == "" or server_token == "" or repo_user == "" or gitee_token == "" or not_cibot_gitee_token == "" or \
            user_email == "" or user_pass == "" or mail_server == "":
        logging.error("args can not be empty")
        return
    # config git
    config_git()

    # config get-mail tools
    config_get_mail(user_email, user_pass, mail_server, "/home/patchwork/patchwork/patchwork/bin/parsemail.sh")

    # get mail from email address
    get_mail_step()

    information = get_project_and_series_information()
    if len(information) == 0:
        logging.info("not a new series of patches which received by get-mail tool")
        return

    for i in information:
        project_name = i.split(":")[0]
        series_id = i.split(":")[1]

        tag = i.split(":")[2].split("[")[1].split("]")[0]
        if "PR" not in tag:
            continue
        
        branch = ""
        if tag.__contains__(","):
            if tag.count(",") == 1:
                branch = tag.split(",")[1]
            elif tag.count(",") >= 2:
                if tag.split(",")[-1] == project_name:
                    branch = tag.split(",")[-1]
                else:
                    branch = tag.split(",")[-2]
        else:
            branch = tag

        config_git_pw(project_name, server, server_token)

        # download series of patches by series_id
        download_patches_by_using_git_pw(series_id)

        # get sender email and cover-letter-body
        sender_email, letter_body, sync_pr = get_email_content_sender_and_covert_to_pr_body(series_id)

        emails_to_notify = [sender_email]

        # use patches
        target_branch = BRANCHES_MAP.get(branch)
        if target_branch is None:
            continue
        source_branch = make_branch_and_apply_patch(repo_user, not_cibot_gitee_token, target_branch, series_id)

        # make pr
        make_pr_to_summit_commit(source_branch, target_branch, not_cibot_gitee_token,
                                 sync_pr, letter_body, emails_to_notify)


if __name__ == '__main__':
    main()
