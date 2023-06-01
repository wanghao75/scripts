import base64
import re
import time
import requests
import os
import email
import imaplib
import smtplib
import psycopg2
from email.utils import make_msgid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from textwrap import dedent

BRANCHES_MAP = {
    "src-openeuler/kernel": {
        'build-5.10-rc': 'build-5.10-rc',
        'master': 'master',
        'openEuler-20.03-LTS': 'openEuler-20.03-LTS',
        'openEuler-20.03-LTS-Next': 'openEuler-20.03-LTS-Next',
        'openEuler-20.03-LTS-SP1': 'openEuler-20.03-LTS-SP1',
        'openEuler-20.03-LTS-SP1-testing': 'openEuler-20.03-LTS-SP1-testing',
        'openEuler-20.03-LTS-SP2': 'openEuler-20.03-LTS-SP2',
        'openEuler-20.03-LTS-SP3': 'openEuler-20.03-LTS-SP3',
        'openEuler-20.09': 'openEuler-20.09',
        'openEuler-21.03': 'openEuler-21.03',
        'openEuler-21.09': 'openEuler-21.09',
        'openEuler-22.03-LTS': 'openEuler-22.03-LTS',
        'openEuler-22.03-LTS-LoongArch': 'openEuler-22.03-LTS-LoongArch',
        'openEuler-22.03-LTS-Next': 'openEuler-22.03-LTS-Next',
        'openEuler-22.03-LTS-SP1': 'openEuler-22.03-LTS-SP1',
        'openEuler-22.09': 'openEuler-22.09',
        'openEuler-22.09-HeXin': 'openEuler-22.09-HeXin',
        'openEuler-23.03': 'openEuler-23.03',
        'openEuler1.0': 'openEuler1.0',
        'openEuler1.0-base': 'openEuler1.0-base'
    },
    "openeuler/kernel": {
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
}

# map of getmailrc file path, host and pass
RCFile_MAP = {
    "/home/patches/rc/src-openeuler/kernel": {"host": "SRC_OPENEULER_KERNEL_HOST", "pass": "SRC_OPENEULER_KERNEL_PASS"},
    "/home/patches/rc/openeuler/kernel": {"host": "OPENEULER_KERNEL_HOST", "pass": "OPENEULER_KERNEL_PASS"}
}

PR_SUCCESS = "反馈：\n" \
             "您发送到{}的补丁/补丁集，已成功转换为PR！\n" \
             "PR链接地址： {}\n" \
             "邮件列表地址：{}\n" \
             "\nFeedBack:\n" \
             "The patch(es) which you have sent to mailing list has been converted to a pull request successfully!\n" \
             "Pull request link: {}\n" \
             "Mailing list address: {}\n"

PR_FAILED = "反馈:\n" \
            "您发送到{}的补丁/补丁集，转换为PR失败！\n" \
            "邮件列表地址：{}\n" \
            "失败原因：{}\n" \
            "建议解决方法：{}\n" \
            "\nFeedBack:\n" \
            "The patch(es) which you have sent to {} has been converted to PR failed!" \
            "Mailing list address: {}\n" \
            "Failed Reason: {}\n" \
            "Suggest Solution: {}\n"


def make_fork_same_with_origin(branch_name, o, r):
    """
    use this function to make the fork repository same with the source repository
    :param branch_name: origin branch
    :param o: organization
    :param r: repo name
    :return:
    """
    remotes = os.popen("git remote -v").readlines()
    remote_flag = False
    for remote in remotes:
        if remote.startswith("upstream "):
            remote_flag = False
        else:
            remote_flag = True

    same_flag = True
    if remote_flag:
        if o == "src-openeuler":
            os.popen("git remote add upstream https://gitee.com/new-op-src/{}.git".format(r))
        elif o == "openeuler":
            os.popen("git remote add upstream https://gitee.com/new-op/{}.git".format(r))

    if branch_name in ["openEuler-1.0-LTS", "master"]:
        os.popen("git checkout -f {}".format(branch_name)).readlines()
    else:
        os.popen("git checkout -f origin/{}".format(branch_name)).readlines()
    fetch_res = os.popen("git fetch upstream {}".format(branch_name)).readlines()
    for p in fetch_res:
        if "error:" in p or "fatal:" in p:
            print("fetch upstream error %s" % p)
            same_flag = False
    merge = os.popen("git merge upstream/{}".format(branch_name)).readlines()
    for m in merge:
        if "error:" in m or "fatal:" in m:
            print("merge upstream error %s" % m)
            same_flag = False

    push_res = os.popen("git push origin HEAD:{}".format(branch_name)).readlines()
    for s in push_res:
        if "error:" in s or "fatal:" in s:
            print("push error %s" % s)
            same_flag = False

    return same_flag


def get_mail_step():
    # before run getmail, sleep 5 minutes
    # time.sleep(300)
    # 兼容多仓库
    for k, v in RCFile_MAP.items():
        os.environ["GET_EMAIL"] = os.getenv(v.get("host"))
        # os.popen("export GET_EMAIL=%s" % os.getenv(v.get("host"))).readlines()
        os.popen('getmail --getmaildir="{}" --idle INBOX'.format(k)).readlines()
        time.sleep(10)


def download_patches_by_using_git_pw(ser_id):
    if not os.path.exists("/home/patches/{}".format(ser_id)):
        os.popen("mkdir -p /home/patches/{}".format(ser_id))
    retry = 0
    while True:
        if retry < 3:
            os.popen("git-pw series download {} /home/patches/{}/".format(ser_id, ser_id)).readlines()
            retry += 1
        else:
            break


def get_project_and_series_information():
    if not os.path.exists("/home/patches/project_series.txt"):
        return []
    with open("/home/patches/project_series.txt", "r", encoding="utf-8") as f:
        infor = f.readlines()

    return infor


def config_git(git_email, git_name):
    os.popen("git config --global user.email {};git config --global user.name '{}'".format(git_email, git_name))


def un_config_git():
    # make sure not push code to git by using the before one's information while git config not work
    os.popen("git config --global --unset user.name")
    os.popen("git config --global --unset user.email")


def config_get_mail(rc_path, u_name, u_pass, email_server, path_of_sh):
    file_path = "{}/getmailrc".format(rc_path)
    if os.path.exists(file_path):
        with open("{}/getmailrc".format(rc_path), "r", encoding="utf-8") as ff:
            content = ff.readlines()
            if len(content) == 0:
                os.popen("rm -f {}/getmailrc".format(rc_path)).readlines()
                os.popen("touch {}/getmailrc".format(rc_path)).readlines()
            else:
                return
    else:
        os.popen("touch {}".format(file_path)).readlines()

    retriever = ["[retriever]", "type = SimplePOP3SSLRetriever",
                 "server = {}".format(email_server),
                 "username = {}".format(os.getenv(u_name, "")),
                 "password = {}".format(os.getenv(u_pass, "")),
                 "port = {}".format(os.getenv("EMAIL_PORT"))
                 ]

    destination = ["[destination]", "type = MDA_external", "path = {}".format(path_of_sh), "ignore_stderr = true"]

    options = ["[options]", "delete = false", "message_log = {}/getmail.log".format(rc_path),
               "message_log_verbose = true", "read_all = false", "received = false", "delivered_to = false"]

    with open(file_path, "a", encoding="utf-8") as f:
        f.writelines([r + "\n" for r in retriever])
        f.writelines([r + "\n" for r in destination])
        f.writelines([r + "\n" for r in options])


def config_git_pw(project_name, server_link, token):
    os.popen("git config --global pw.server {};git config --global pw.token {};git config --global pw.project {}"
             .format(server_link, token, project_name)).readlines()


# if use the patchwork, we can make it by the following codes
# use patches
def make_branch_and_apply_patch(user, token, origin_branch, ser_id, repository_path):
    org = repository_path.split("/")[0]
    repo_name = repository_path.split("/")[1]
    if not os.path.exists("/home/patches/{}".format(repository_path)):
        os.chdir("/home/patches/{}".format(org))
        if org.__contains__("src-"):
            r = os.popen("git clone https://{}:{}@gitee.com/src-wq/{}.git".format(user, token, repo_name)).readlines()
            for res in r:
                if "error:" in res or "fatal:" in res:
                    os.popen(
                        "git clone https://{}:{}@gitee.com/src-wq/{}.git".format(user, token, repo_name)).readlines()
            os.chdir("/home/patches/{}".format(repository_path))
        else:
            r = os.popen("git clone https://{}:{}@gitee.com/patch-bot/{}.git".format(user, token, repo_name)).readlines()
            for res in r:
                if "error:" in res or "fatal:" in res:
                    os.popen(
                        "git clone https://{}:{}@gitee.com/patch-bot/{}.git".format(user, token, repo_name)).readlines()
            os.chdir("/home/patches/{}".format(repository_path))
    else:
        os.chdir("/home/patches/{}".format(repository_path))

    same = make_fork_same_with_origin(origin_branch, org, repo_name)

    if not same:
        return "", "", "", ""

    new_branch = "patch-%s" % int(time.time())
    os.popen("git checkout -b %s origin/%s" % (new_branch, origin_branch)).readlines()

    # git am
    patches_dir = "/home/patches/{}/".format(ser_id)
    am_res = os.popen("git am --abort;git am %s*.patch" % patches_dir).readlines()
    am_success = False
    am_failed_reason = ""

    for am_r in am_res:
        if am_r.__contains__("Patch failed at"):
            am_success = False
            am_failed_reason = am_r
            print("failed to apply patch, reason is %s" % am_r)
            break
        else:
            am_success = True

    if am_success:
        retry_flag = False
        push_res = os.popen("git push origin %s" % new_branch).readlines()
        for p in push_res:
            if "error:" in p or "fatal:" in p:
                time.sleep(5)
                print("git push failed, %s, try again" % p)
                os.popen("git push origin %s" % new_branch).readlines()
                retry_flag = True

        if retry_flag:
            os.popen("git push origin %s" % new_branch).readlines()
        # un_config_git()
        return new_branch, org, repo_name, am_failed_reason
    else:
        # un_config_git()
        return new_branch, org, repo_name, am_failed_reason


# summit a pr
def make_pr_to_summit_commit(org, repo_name, source_branch, base_branch, token, pr_url_in_email_list, cover_letter, receiver_email,
                             pr_title, commit, cc_email, sub, msg_id):
    title = pr_title
    if pr_url_in_email_list or cover_letter:
        body = "PR sync from: {}\n{} \n{}".format(commit, pr_url_in_email_list, cover_letter)
    else:
        body = ""

    create_pr_url = ""
    if org == "src-openeuler":
        create_pr_url = "https://gitee.com/api/v5/repos/new-op-src/{}/pulls".format(repo_name)
    elif org == "openeuler":
        create_pr_url = "https://gitee.com/api/v5/repos/new-op/{}/pulls".format(repo_name)

    data = {
        "access_token": token,
        "head": "patch-bot:" + source_branch,
        "base": base_branch,
        "title": title,
        "body": body,
        "prune_source_branch": "true"
    }
    if org == "src-openeuler":
        data["head"] = "src-wq:" + source_branch

    res = requests.post(url=create_pr_url, data=data)

    try_times = 0
    while True:
        if res.status_code != 201:
            if try_times >= 2:
                break
            res = requests.post(url=create_pr_url, data=data)
            try_times += 1
        else:
            break

    pr_failed_reason = ""

    if res.status_code == 201:
        pull_link = res.json().get("html_url")
        content = PR_SUCCESS.format(cc_email[0], pull_link, pr_url_in_email_list,
                                    cc_email[0], pull_link, pr_url_in_email_list)
        send_mail_to_notice_developers(
            content, receiver_email, cc_email, sub, msg_id, org + "/" + repo_name
        )

        # add /check-cla comment to pr
        comment_data = {
            "access_token": token,
            "body": "/check-cla",
        }

        comment_url = ""
        if org == "src-openeuler":
            comment_url = "https://gitee.com/api/v5/repos/new-op-src/{}/pulls/{}/comments".\
                format(repo_name, res.json().get("number"))
        elif org == "openeuler":
            comment_url = "https://gitee.com/api/v5/repos/new-op/{}/pulls/{}/comments".\
                format(repo_name, res.json().get("number"))

        rsp = requests.post(url=comment_url, data=comment_data)

        if rsp.status_code != 201:
            requests.post(url=comment_url, data=comment_data)

        return True, pr_failed_reason
    else:
        if len(res.json()) != 0:
            pr_failed_reason = res.json().get("message")
        else:
            pr_failed_reason = "Unknown error"
        return False, pr_failed_reason


# use email to notice that pr has been created
def send_mail_to_notice_developers(content, email_address, cc_address, subject, message_id, repo_path):
    env_host_user = ""
    env_host_pass = ""
    for k, v in RCFile_MAP.items():
        if repo_path in k:
            env_host_user = v.get("host")
            env_host_pass = v.get("pass")
    useraccount = os.getenv("%s" % env_host_user, "")
    password = os.getenv("%s" % env_host_pass, "")
    imap_server = 'imap.163.com'
    im_server = imaplib.IMAP4_SSL(imap_server, 993)
    im_server.login(useraccount, password)

    sm_server = smtplib.SMTP(os.getenv("SEND_EMAIL_HOST", "smtp.163.com"), os.getenv("SEND_EMAIL_PORT", 25))
    sm_server.ehlo()
    sm_server.starttls()
    sm_server.login(useraccount, password)

    imaplib.Commands['ID'] = ('AUTH')
    args = ("name", "{}".format(useraccount), "contact",
            "{}".format(useraccount), "version", "1.0.0", "vendor", "myclient")
    im_server._simple_command('ID', '("' + '" "'.join(args) + '")')
    im_server.select()
    _, unseen = im_server.search(None, "UNANSWERED")
    unseen_list = unseen[0].split()

    for number in unseen_list:
        _, data = im_server.fetch(number, '(RFC822)')
        original = email.message_from_bytes(data[0][1])
        from_email = original["From"]
        if "<" in from_email and ">" in from_email:
            from_email = original["From"].split("<")[1].split(">")[0]
        else:
            from_email = from_email.strip(" ")
        if from_email == email_address[0] and original['Message-ID'] == message_id:
            sm_server.sendmail(useraccount, email_address + cc_address,
                               create_auto_reply(useraccount, email_address, content, cc_address, original).as_bytes())
            log = 'Replied to “%s” for the mail “%s”' % (original['From'],
                                                         original['Subject'])
            print(log)
            im_server.store(number, '+FLAGS', '\\Answered')

    sm_server.quit()
    sm_server.close()
    im_server.logout()


# get origin content
def create_auto_reply(from_address, to_address, body, cc_address, original):
    mail = MIMEMultipart('alternative')
    mail['Message-ID'] = make_msgid()
    mail['References'] = mail['In-Reply-To'] = original['Message-ID']
    mail['Subject'] = 'Re: ' + original['Subject']
    mail['From'] = "patchwork bot <{}>".format(from_address)
    mail['To'] = ",".join(to_address)
    mail['Cc'] = ",".join(cc_address)
    mail.attach(MIMEText(dedent(body), 'plain'))
    return mail


def get_email_content_sender_and_covert_to_pr_body(ser_id, path_of_repo):
    user = os.getenv("DATABASE_USER")
    name = os.getenv("DATABASE_NAME")
    password = os.getenv("DATABASE_PASSWORD")
    host = os.getenv("DATABASE_HOST")

    conn = psycopg2.connect(database=name, user=user, password=password, host=host, port="5432")

    cur = conn.cursor()

    cur.execute("SELECT * from patchwork_series where id={}".format(ser_id))
    series_rows = cur.fetchall()
    cover_letter_id = 0
    # all_patches_in_series = 0
    for row in series_rows:
        cover_letter_id = row[-1]
        # all_patches_in_series = row[4]

    # no cover
    patch_sender_email = ""
    patch_send_name = ""
    body = ""
    email_list_link_of_patch = ""
    title_for_pr = ""
    committer = ""
    sub = ""
    cc = []
    msg_id = ""

    if cover_letter_id is None or cover_letter_id == 0:
        cur.execute("SELECT name from patchwork_patch where series_id={}".format(ser_id))
        patches_names_rows = cur.fetchall()
        first_path_mail_name = ""
        if len(patches_names_rows) == 1:
            first_path_mail_name = patches_names_rows[0][0]
            title_for_pr = first_path_mail_name.split("]")[1]
            sub = first_path_mail_name
        else:
            for row in patches_names_rows:
                if row[0].__contains__("01/") or row[0].__contains__("1/"):
                    first_path_mail_name = row[0]

        cur.execute(
            "SELECT headers from patchwork_patch where series_id={} and name='{}'".format(ser_id, first_path_mail_name))
        patches_headers_rows = cur.fetchall()
        who_is_email_list = ""
        for row in patches_headers_rows:
            data = row[0].split("\n")
            for index, string in enumerate(data):
                if string.startswith("To: "):
                    if "<" in string:
                        who_is_email_list = string.split("<")[1].split(">")[0]
                    else:
                        who_is_email_list = string.split(" ")[1]
                if string.startswith("From: "):
                    if "<" not in string and ">" not in string:
                        email_from = data[index + 1]
                        email_from_name = base64.b64decode(string.split("From: ")[1].split("?b?")[1].split("?=")[0]) \
                            .decode("gb18030")
                        committer = email_from_name + " " + email_from
                        patch_sender_email = email_from.split("<")[1].split(">")[0]
                        patch_send_name = email_from_name
                    else:
                        committer = string.split("From:")[1]
                        patch_sender_email = string.split("<")[1].split(">")[0]
                        patch_send_name = string.split("<")[0].split("From:")[1].split(" ")[1] + " " + \
                                          string.split("<")[0].split("From:")[1].split(" ")[2]
                if string.__contains__("https://mailweb.openeuler.org/hyperkitty/list/%s/message/" % who_is_email_list):
                    email_list_link_of_patch = string.replace("<", "").replace(">", "").replace("message", "thread")
                if string.startswith("Message-Id: "):
                    msg_id = string.split("Message-Id: ")[1]
                if string.startswith("Message-ID: "):
                    msg_id = string.split("Message-ID: ")[1]
        cc.append(who_is_email_list)

        if "1/" in first_path_mail_name:
            zh_reason = "补丁集缺失封面信息"
            zh_suggest = "请提供补丁集并重新发送您的补丁集到邮件列表"
            en_reason = "the cover of the patches is missing"
            en_suggest = "please checkout and apply the patches' cover and send all again"
            content = PR_FAILED.format(cc[0], email_list_link_of_patch, zh_reason, zh_suggest, 
                                       cc[0], email_list_link_of_patch, en_reason, en_suggest)
            send_mail_to_notice_developers(content, [patch_sender_email], [], sub, msg_id, path_of_repo)
            cur.close()
            conn.close()
            return "", "", "", "", "", "", "", ""

        # config git
        config_git(patch_sender_email, patch_send_name)
        cur.close()
        conn.close()

        return patch_sender_email, body, email_list_link_of_patch, title_for_pr, committer, cc, sub, msg_id

    cur.execute("SELECT * from patchwork_cover where id={}".format(cover_letter_id))
    cover_rows = cur.fetchall()
    cover_headers = ""
    cover_content = ""
    cover_name = ""
    for row in cover_rows:
        cover_name = row[5]
        cover_headers = row[3]
        cover_content = row[4]

    if cover_content == "" or cover_headers == "" or cover_name == "":
        cur.close()
        conn.close()
        return "", "", "", "", "", "", "", ""
    sub = cover_name
    title_for_pr = cover_name.split("]")[1]

    cover_who_is_email_list = ""
    cover_data = cover_headers.split("\n")
    for idx, ch in enumerate(cover_data):
        if ch.startswith("Message-Id: "):
            msg_id = ch.split("Message-Id: ")[1]
        if ch.startswith("Message-ID: "):
            msg_id = ch.split("Message-ID: ")[1]
        if ch.startswith("To: "):
            if "<" in ch:
                cover_who_is_email_list = ch.split("<")[1].split(">")[0]
            else:
                cover_who_is_email_list = ch.split(" ")[1]
        if ch.__contains__("https://mailweb.openeuler.org/hyperkitty/list/%s/message/" % cover_who_is_email_list):
            email_list_link_of_patch = ch.replace("<", "").replace(">", "").replace("message", "thread")
        if ch.startswith("From: "):

            if "<" not in ch and ">" not in ch:
                email_from = cover_data[idx + 1]
                email_from_name = base64.b64decode(ch.split("From: ")[1].split("?b?")[1].split("?=")[0]) \
                    .decode("gb18030")
                committer = email_from_name + " " + email_from
                patch_sender_email = email_from.split("<")[1].split(">")[0]
                patch_send_name = email_from_name
            else:
                committer = ch.split("From:")[1]
                patch_sender_email = ch.split("<")[1].split(">")[0]
                patch_send_name = ch.split("<")[0].split("From:")[1].split(" ")[1] + " " + \
                                  ch.split("<")[0].split("From:")[1].split(" ")[2]
    cc.append(cover_who_is_email_list)

    for ct in cover_content.split("\n"):
        if ct.__contains__("(+)") or ct.__contains__("(-)") or "mode" in ct or "| " in ct:
            continue
        else:
            cur.execute("select name from patchwork_patch where series_id={}".format(ser_id))
            patch_number = cur.fetchall()
            if len(patch_number) == 1:
                body = ""
            else:
                body += ct + "\n"

    # config git
    config_git(patch_sender_email, patch_send_name)

    cur.close()
    conn.close()

    return patch_sender_email, body, email_list_link_of_patch, title_for_pr, committer, cc, sub, msg_id


def check_patches_number_same_with_subject(ser_id, tag_str):
    user = os.getenv("DATABASE_USER")
    name = os.getenv("DATABASE_NAME")
    password = os.getenv("DATABASE_PASSWORD")
    host = os.getenv("DATABASE_HOST")

    conn = psycopg2.connect(database=name, user=user, password=password, host=host, port="5432")

    cur = conn.cursor()
    cur.execute("SELECT count(*) from patchwork_patch where series_id={}".format(ser_id))
    in_db = cur.fetchall()
    patch_number_db = in_db[0][0]

    number_re = re.compile(r'\d+/\d+')
    if tag_str.count(",") < 2:
        if tag_str.count(",") == 0:
            patch_number_subject = 1
        else:
            n = tag_str.split(",")[-1]
            if number_re.match(n):
                patch_number_subject = int(n.split("/")[1])
            else:
                patch_number_subject = 1
    else:
        patch_number_subject = int(tag_str.split(",")[-1].split("/")[1])

    cur.close()
    conn.close()
    print("number in db: ", patch_number_db, " number in sub: ", patch_number_subject)
    if patch_number_db != patch_number_subject:
        return False

    return True


def change_email_status_to_answered(host_pass_dict):
    useraccount = os.getenv("%s" % host_pass_dict.get("host"), "")
    password = os.getenv("%s" % host_pass_dict.get("pass"), "")
    imap_server = 'imap.163.com'
    im_server = imaplib.IMAP4_SSL(imap_server, 993)
    im_server.login(useraccount, password)

    imaplib.Commands['ID'] = ('AUTH')
    args = ("name", "{}".format(useraccount), "contact", "{}".format(useraccount), "version", "1.0.0", "vendor", "myclient")
    im_server._simple_command('ID', '("' + '" "'.join(args) + '")')
    im_server.select()
    _, unseen = im_server.search(None, "UNANSWERED")
    unseen_list = unseen[0].split()

    for number in unseen_list:
        im_server.store(number, '+FLAGS', '\\Answered')
    im_server.logout()


def rewrite_to_project_series_file(data_list):
    if os.path.exists("/home/patches/project_series.txt"):
        os.remove("/home/patches/project_series.txt")
    with open("/home/patches/project_series.txt", "a", encoding="utf-8") as f:
        for d in data_list:
            f.writelines(d)


def main():
    server = os.getenv("PATCHWORK_SERVER", "")
    server_token = os.getenv("PATCHWORK_TOKEN", "")
    repo_user = os.getenv("CI_BOT_NAME", "")
    not_cibot_gitee_token = os.getenv("GITEE_TOKEN_NOT_CI_BOT", "")
    mail_server = os.getenv("EMAIL_HOST", "")

    if server == "" or server_token == "" or repo_user == "" or not_cibot_gitee_token == "" or mail_server == "":
        print("args can not be empty")
        return

    # config get-mail tools
    for k, v in RCFile_MAP.items():
        config_get_mail(k, v.get("host"), v.get("pass"), mail_server,
                        "/home/patchwork/patchwork/patchwork/bin/parsemail.sh")

    # get mail from email address
    get_mail_step()

    information = get_project_and_series_information()
    if len(information) == 0:
        print("not a new series of patches which received by get-mail tool has been write to file")
        return

    infor_data = []
    for i in information:
        list_id = i.split(":")[0]
        repo = ""
        for k, v in RCFile_MAP.items():
            if os.getenv(v.get("host")) == list_id:
                repo = k.split("/")[-2] + "/" + k.split("/")[-1]

        project_name = i.split(":")[1]

        rep = repo.replace("/", "-")
        tag_name = i.split(":")[1].replace("%s-" % rep, "")

        series_id = i.split(":")[2]

        tag = i.split(":")[3].split("[")[1].split("]")[0]

        # check if we have the same number of patches in db, if not, skip
        same_in_db = check_patches_number_same_with_subject(series_id, tag)
        if not same_in_db:
            infor_data.append(i)
            information.remove(i)
            print("getmail did not pull all emails from %s, so skip" % i)
            continue

        branch = ""
        if tag.__contains__(","):
            if tag.count(",") == 1:
                if tag.split(",")[-1] == tag_name:
                    branch = tag.split(",")[-1]
                else:
                    branch = tag.split(",")[0]
            elif tag.count(",") >= 2:
                if tag.split(",")[-1] == tag_name:
                    branch = tag.split(",")[-1]
                else:
                    branch = tag.split(",")[0]
        else:
            branch = tag

        # in production environment， deploy on one branch
        branch = branch.strip(" ")
        # if branch not in ["openEuler-22.03-LTS-SP1", "openEuler-22.03-LTS", "OLK-5.10"] and repo == "openeuler/kernel":
        #     print("branch doesn't match, ignore it")
        #     continue

        config_git_pw(project_name, server, server_token)

        # download series of patches by series_id
        download_patches_by_using_git_pw(series_id)

        # get sender email and cover-letter-body
        sender_email, letter_body, sync_pr, title_pr, comm, cc, subject_str, message_id = get_email_content_sender_and_covert_to_pr_body(
            series_id, repo)

        if sender_email == "" and letter_body == "" and sync_pr == "" and title_pr == "":
            print("can not get useful information for ", project_name, ", series id is ", series_id, ", repo is ", repo)
            continue

        emails_to_notify = [sender_email]
        cc_list = cc

        # use patches
        target_branch = BRANCHES_MAP.get(repo).get(branch)
        branch_not_match = False
        if target_branch is None:
            branch_not_match = True
        else:
            if repo == "openeuler/kernel" \
                    and target_branch not in ["openEuler-22.03-LTS-SP1", "openEuler-22.03-LTS", "OLK-5.10"]:
                branch_not_match = True

        if branch_not_match:
            print("branch is ", branch, "can not match any branches")
            zh_reason = "补丁/补丁集的标题分支与仓库分支列表不匹配"
            zh_suggest = "请确认补丁标题分支，若有误则修改，无则忽略"
            en_reason = "branch in patch(es)'s title can not match any branches in repository's branch list"
            en_suggest = "please checkout if the patch(es)'s title is wrong and fix it, if not ignore this"
            content = PR_FAILED.format(
                cc[0], sync_pr, zh_reason, zh_suggest, cc[0], sync_pr, en_reason, en_suggest
            )

            send_mail_to_notice_developers(
                content, emails_to_notify, [], subject_str, message_id, repo
            )
            continue

        source_branch, organization, rp, failed_reason = make_branch_and_apply_patch(
            repo_user, not_cibot_gitee_token, target_branch, series_id, repo)

        if failed_reason != "":
            zh_reason = "应用补丁/补丁集失败，%s" % failed_reason
            zh_suggest = "请查看失败原因， 确认补丁是否可以应用在当前期望分支的最新代码上"
            en_reason = "apply patch(es) failed, %s" % failed_reason
            en_suggest = "please checkout if the failed patch(es) can work on the newest codes in expected branch"
            content = PR_FAILED.format(
                cc[0], sync_pr, zh_reason, zh_suggest, cc[0], sync_pr, en_reason, en_suggest
            )

            send_mail_to_notice_developers(
                content, emails_to_notify, [], subject_str, message_id, repo
            )
            continue

        if source_branch == "" or organization == "" or rp == "":
            information.remove(i)
            infor_data.append(i)

            zh_reason = "同步源码仓代码到fork仓失败"
            zh_suggest = "请稍等，机器人会在下一次任务重新执行"
            en_reason = "sync origin kernel's codes to the fork repository failed"
            en_suggest = "please wait, the bot will retry in the next interval"
            content = PR_FAILED.format(
                cc[0], sync_pr, zh_reason, zh_suggest, cc[0], sync_pr, en_reason, en_suggest
            )

            # sync codes from origin failed, so send email to tell developer what happened
            send_mail_to_notice_developers(content, emails_to_notify, [], subject_str, message_id, repo)
            continue

        # make pr
        pr_success, reason = make_pr_to_summit_commit(organization, rp, source_branch, target_branch, not_cibot_gitee_token,
                                 sync_pr, letter_body, emails_to_notify, title_pr, comm, cc_list, subject_str, message_id)

        if not pr_success and reason:
            information.remove(i)
            infor_data.append(i)

            zh_reason = "调用gitee api创建PR失败， 失败原因如下： %s" % reason
            zh_suggest = "请稍等，机器人会在下一次任务重新执行"
            en_reason = "create PR failed when call gitee's api, failed reason is as follows: %s" % reason
            en_suggest = "please wait, the bot will retry in the next interval"
            content = PR_FAILED.format(
                cc[0], sync_pr, zh_reason, zh_suggest, cc[0], sync_pr, en_reason, en_suggest
            )

            # call gitee api to create PR failed, so send mail to tell developers what happened and take easy
            send_mail_to_notice_developers(content, emails_to_notify, [], subject_str, message_id, repo)
            continue

    if len(infor_data) != 0:
        rewrite_to_project_series_file(infor_data)
    else:
        os.remove("/home/patches/project_series.txt")
        # for v in RCFile_MAP.values():
        #     change_email_status_to_answered(v)


if __name__ == '__main__':
    main()
