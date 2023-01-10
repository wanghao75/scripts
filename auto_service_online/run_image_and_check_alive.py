import os
import sys
import time

import requests
import yaml


def load_checklist_yaml():
    with open("./checklist.yaml", "r", encoding="utf-8") as f:
        data = yaml.load(f.read(), Loader=yaml.SafeLoader)

    if len(data) == 0:
        print("no data")
        sys.exit(1)

    return data


def use_kubectl_to_deploy_project(project):
    check_pod_in_test_workspace(project)
    work = os.popen("kubectl apply -f deploy.yaml --kubeconfig test-cluster-deploy-workspace.config")
    for op in work.readlines():
        if not op.replace("\n", "").endswith("created"):
            print("apply pod to cluster failed")
            return False
    return True


def check_pod_in_test_workspace(project):
    for line in os.popen("kubectl get pods -n deploy-workspace --kubeconfig test-cluster-deploy-workspace.config")\
            .readlines():
        if line.__contains__(project):
            os.popen("kubectl delete deployment %s -n deploy-workspace "
                     "--kubeconfig test-cluster-deploy-workspace.config" % project)


def check_pods_alive():
    alive = False
    for line in os.popen("kubectl get pods -n deploy-workspace --kubeconfig test-cluster-deploy-workspace.config")\
            .readlines():
        if line.__contains__("RUNNING"):
            alive = True
            break
    return alive


def replace_test_to_product(project):
    os.popen("sed -i 's/deploy-workspace/%s/g' `grep deploy-workspace -rl ./output" % project)


def prepare_for_pr(gh_user, ge_user, gh_token, ge_token, gh_email, ge_email, community):
    if community == "opengauss":
        upstream = "https://gitee.com/wanghaosq/infra"
        clone_cmd = "git clone https://oauth2:{}@gitee.com/{}/infra".format(ge_token, ge_user)
        os.system(clone_cmd)
        path = os.popen("pwd").read()
        os.chdir("infra")
        os.system("git config user.name {};git config user.email {};"
                  "git remote add upstream {};git fetch upstream;git rebase upstream/master"
                  .format(ge_user, ge_email, upstream))

        branch = os.getenv("PROJECT") + "_%d" % int(time.time())
        os.chdir("deploy")
        os.system(
            "mkdir {};cp -r ../../output/* {};git checkout -b {};git add .;git commit -am {};git push -u origin {}"
            .format(os.getenv("PROJECT"), os.getenv("PROJECT"), branch, "add new service files", branch))

        os.system('curl \
                  -X POST \
                  -header "Content-Type: application/json;charset=UTF-8" \
                  https://gitee.com/api/v5/repos/wanghaosq/infra/pulls \
                  -d "{\"access_token\":\"{}\", \"title\":\"{}\",\"head\":\"{}:{}\",\"base\":\"master\",\"prune_source_branch\":\"true\"}"'
                  .format(ge_token, "add new service", ge_user, branch))
        os.chdir(path)

    if community in ["openeuler", "openlookeng", "mindspore"]:
        upstream = "https://github.com/wanghao75/infra-%s" % community
        repo = "infra-" + community
        clone_cmd = "git clone https://oauth2:{}@github.com/{}/{}".format(gh_token, gh_user, repo)
        os.system(clone_cmd)
        path = os.popen("pwd").read()
        os.chdir("%s" % repo)
        os.system("git config user.name {};git config user.email {};"
                  "git remote add upstream {};git fetch upstream;git rebase upstream/master"
                  .format(gh_user, gh_email, upstream))

        branch = os.getenv("PROJECT") + "_%d" % int(time.time())
        os.chdir("applications")
        os.system("mkdir {};cp -r ../../output/* {};git checkout -b {};git add .;git commit -am {};git push -u origin {}"
                  .format(repo, os.getenv("PROJECT"), os.getenv("PROJECT"), branch, "add new service files", branch))

        os.system('curl \
          -X POST \
          -H "Accept: application/vnd.github.v3+json" \
          -H "Authorization: Bearer {}" \
          https://api.github.com/repos/wanghao75/{}/pulls \
          -d "{\"title\":\"{}\",\"head\":\"{}:{}\",\"base\":\"master\",\"prune_source_branch\":\"true\"}"'
                  .format(gh_token, repo, "add new service", gh_user, branch))
        os.chdir(path)


def feed_back_to_pr(response_pr: bool, reason: str, t: str, o: str, r: str, n: str):
    if response_pr:
        gitee_api = "https://gitee.com/api/v5/repos/{}/{}/pulls/{}/comments".format(o, r, n)

        data = {
            "access_token": t,
            "body": "Deploy service to test environment failed, {}, please check your checklist.yaml,"
                    " if there is nothing wrong with it, or if you have no idea about how to fix it, "
                    "contact with @ (刘洋) to get some help.".format(reason)
        }
        requests.post(url=gitee_api, data=data)


def remove_pods_in_test_environment():
    os.system("kubectl delete -f deploy.yaml")


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

    data = load_checklist_yaml()
    prj = data.get("project")
    cmt = data.get("community")

    # deploy to test cluster
    deploy_status = use_kubectl_to_deploy_project(prj)
    if not deploy_status:
        feed_back_to_pr(True, "because apply this project to test cluster failed", gee_token, org, repo, number)
        sys.exit(1)

    # check pods alive
    status = check_pods_alive()
    if status:
        replace_test_to_product(prj)
        prepare_for_pr(ghub_user, gee_user, ghub_token, gee_token, ghub_email, gee_email, cmt)
        remove_pods_in_test_environment()

    else:
        feed_back_to_pr(True, "because pod that has been applied to test cluster is not alive, service is unreachable",
                        gee_token, org, repo, number)
        sys.exit(1)


if __name__ == '__main__':
    main()
