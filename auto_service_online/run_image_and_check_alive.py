import os
import sys
import time

import requests


def pull_image_from_swr(image: str):
    run_status = os.system("docker pull %s" % image)
    if run_status != 0:
        print("pull image to local failed")
        return False
    return True


def use_kubectl_to_deploy_project():
    work = os.popen("kubectl apply -f deploy.yaml")
    for op in work.readlines():
        if not op.endswith("created"):
            print("apply pod to cluster failed")
            return False
    return True


def check_pods_alive(ns, pj):
    alive = False
    for line in os.popen("kubectl get pods --namespace %s | grep %s | grep -v 'grep'" % (ns, pj)).readlines():
        if line.__contains__("RUNNING"):
            alive = True
            break
    return alive


def prepare_for_pr(gh_user, ge_user, gh_token, ge_token, gh_email, ge_email, community):
    if community == "opengauss":
        upstream = "https://gitee.com/opengauss/infra"
        clone_cmd = "git clone https://oauth2:{}@gitee.com/{}/infra".format(ge_token, ge_user)
        os.system(clone_cmd)
        path = os.popen("pwd").read()
        os.system("cd infra")
        os.system("git config user.name {};git config user.email {};"
                  "git remote add upstream {};git fetch upstream;git rebase upstream/master;cd {}"
                  .format(ge_user, ge_email, upstream, path))

        branch = os.getenv("PROJECT") + "_%d" % int(time.time())
        os.system(
            "cd infra/deploy;mkdir {};cp -r ../../output/* {};git checkout -b {};git add .;git commit -am {};git push -u origin {}"
            .format(os.getenv("PROJECT"), os.getenv("PROJECT"), branch, "add new service files", branch))

        os.system('curl \
                  -X POST \
                  -header "Content-Type: application/json;charset=UTF-8" \
                  https://gitee.com/api/v5/repos/opengauss/infra/pulls \
                  -d "{\"access_token\":\"{}\", \"title\":\"{}\",\"head\":\"{}:{}\",\"base\":\"master\",\"prune_source_branch\":\"true\"}"'
                  .format(ge_token, "add new service", ge_user, branch))

    if community in ["openeuler", "openlookeng", "mindspore"]:
        upstream = "https://github.com/opensourceways/infra-%s" % community
        repo = "infra-" + community
        clone_cmd = "git clone https://oauth2:{}@github.com/{}/{}".format(gh_token, gh_user, repo)
        os.system(clone_cmd)
        path = os.popen("pwd").read()
        os.system("cd %s" % repo)
        os.system("git config user.name {};git config user.email {};"
                  "git remote add upstream {};git fetch upstream;git rebase upstream/master;cd {}"
                  .format(gh_user, gh_email, upstream, path))

        branch = os.getenv("PROJECT") + "_%d" % int(time.time())
        os.system("cd {}/applications;mkdir {};cp -r ../../output/* {};git checkout -b {};git add .;git commit -am {};git push -u origin {}"
                  .format(repo, os.getenv("PROJECT"), os.getenv("PROJECT"), branch, "add new service files", branch))

        os.system('curl \
          -X POST \
          -H "Accept: application/vnd.github.v3+json" \
          -H "Authorization: Bearer {}" \
          https://api.github.com/repos/opensourceways/{}/pulls \
          -d "{\"title\":\"{}\",\"head\":\"{}:{}\",\"base\":\"master\",\"prune_source_branch\":\"true\"}"'
                  .format(gh_token, repo, "add new service", gh_user, branch))


def feed_back_to_pr(response_pr: bool, reason: str, t: str, o: str, r: str, n: str):
    if response_pr:
        github_api = "https://api.github.com/repos/{}/{}/issues/{}/comments".format(o, r, n)
        headers = {
            "Authorization": t
        }
        data = {
            "body": "Deploy service to test environment failed, {}, please check your checklist.yaml,"
                    " if you have no idea about how to fix it, "
                    "contact with @githubliuyang777 (刘洋) to get some help.".format(reason)
        }
        requests.post(url=github_api, headers=headers, data=data)


def main():
    ghub_token = sys.argv[1]
    org = sys.argv[2]
    repo = sys.argv[3]
    number = sys.argv[4]
    ghub_user = sys.argv[5]
    gee_token = sys.argv[6]
    gee_user = sys.argv[7]
    ghub_email = sys.argv[8]
    gee_email = sys.argv[9]
    if len(sys.argv) != 10:
        print("missing args")
        sys.exit(1)
    pull_status = pull_image_from_swr(os.getenv("IMAGE_ID"))
    if not pull_status:
        feed_back_to_pr(True, "because docker pull image failed", ghub_token, org, repo, number)
    
    # deploy to test cluster
    deploy_status = use_kubectl_to_deploy_project()
    if not deploy_status:
        feed_back_to_pr(True, "because apply project to cluster failed", ghub_token, org, repo, number)
    
    # check pods alive
    status = check_pods_alive(os.getenv("NAMESPACE"), os.getenv("PROJECT"))
    if status:
        prepare_for_pr(ghub_user, gee_user, ghub_token, gee_token, ghub_email, gee_email, os.getenv("COMMUNITY"))
    
    else:
        feed_back_to_pr(True, "because prepare to submit a pr to production environment failed", ghub_token, org, repo, number)


if __name__ == '__main__':
    main()
