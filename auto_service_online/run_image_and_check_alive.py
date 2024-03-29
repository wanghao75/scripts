import json
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
    work = os.popen("kubectl apply -f deploy.yaml -n deploy-workspace --kubeconfig test-cluster-deploy-workspace.config")
    for op in work.readlines():
        if op.replace("\n", "").__contains__("created"):
            return True
    return False


def check_pod_in_test_workspace(project):
    for line in os.popen("kubectl get pods -n deploy-workspace --kubeconfig test-cluster-deploy-workspace.config")\
            .readlines():
        if line.__contains__(project):
            os.popen("kubectl delete deployment %s -n deploy-workspace "
                     "--kubeconfig test-cluster-deploy-workspace.config" % project)


def check_pods_alive():
    # make sure service is healthy
    time.sleep(30)
    alive = False
    for line in os.popen("kubectl get pods -n deploy-workspace --kubeconfig test-cluster-deploy-workspace.config")\
            .readlines():
        if line.__contains__("Running"):
            alive = True
            break
    return alive


def replace_test_to_product(project):
    res = os.popen(r'sed -i "s/deploy-workspace/{}/g" `grep deploy-workspace -rl ./output`'.format(project)).readlines()
    print(res)


def prepare_for_pr(gh_user, ge_user, gh_token, ge_token, gh_email, ge_email, community, proj):
    if community == "opengauss":
        upstream = "https://gitee.com/wanghaosq/infra"
        clone_cmd = "git clone https://oauth2:{}@gitee.com/{}/infra".format(ge_token, ge_user)
        os.system(clone_cmd)
        os.chdir("infra")
        os.system("git config user.name {};git config user.email {};"
                  "git remote add upstream {};git fetch upstream;git rebase upstream/master;"
                  .format(ge_user, ge_email, upstream))

        branch = proj + "_%d" % int(time.time())
        os.chdir("deploy")
        os.system(
            "mkdir {};cp -r ../../output/* {};git checkout -b {};git add .;git commit -am \"{}\";git push -u origin {};"
            .format(proj, proj, branch, "add new service files", branch))

        uri = "https://gitee.com/api/v5/repos/wanghaosq/infra/pulls"
        headers = {"Accept": "application/json"}
        data = {
            "access_token": ge_token,
            "title": "add new service",
            "head": "{}:{}".format(ge_user, branch),
            "base": "master",
            "prune_source_branch": "true"
        }
        requests.post(url=uri, headers=headers, data=data)

    if community in ["openeuler", "openlookeng", "mindspore"]:
        upstream = "https://github.com/wanghao75/infra-%s" % community
        repo = "infra-" + community
        clone_cmd = "git clone https://oauth2:{}@github.com/{}/{}".format(gh_token, gh_user, repo)
        os.system(clone_cmd)
        os.chdir("%s" % repo)
        os.system("git config user.name {};git config user.email {};"
                  "git remote add upstream {};git fetch upstream;git rebase upstream/master;"
                  .format(gh_user, gh_email, upstream))

        branch = proj + "_%d" % int(time.time())
        os.chdir("applications")
        os.system("mkdir {};cp -r ../../output/* {};git checkout -b {};"
                  "git add .;git commit -am \"{}\";git push -u origin {};"
                  .format(proj, proj, branch, "add new service files", branch))

        uri = "https://api.github.com/repos/wanghao75/{}/pulls".format(repo)
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": "token %s" % gh_token
        }
        data = {
            "title": "add new service",
            "head": "{}:{}".format(gh_user, branch),
            "base": "master",
            "prune_source_branch": "true"
        }
        requests.post(url=uri, headers=headers, data=json.dumps(data))


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
    os.system("kubectl delete -f ../../deploy.yaml")


def remove_jobs_in_test_environment(project):
    os.system("kubectl delete cronjob %s" % project)


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
    service_type = data.get("cronjob")

    # deploy to test cluster
    deploy_status = use_kubectl_to_deploy_project(prj)
    if not deploy_status:
        feed_back_to_pr(True, "because apply this project to test cluster failed", gee_token, org, repo, number)
        sys.exit(1)

    # check service is cronjob or not
    if service_type is not None:
        prepare_for_pr(ghub_user, gee_user, ghub_token, gee_token, ghub_email, gee_email, cmt, prj)
        remove_jobs_in_test_environment(prj)

    # check pods alive
    else:
        status = check_pods_alive()
        if status:
            replace_test_to_product(prj)
            prepare_for_pr(ghub_user, gee_user, ghub_token, gee_token, ghub_email, gee_email, cmt, prj)
            remove_pods_in_test_environment()

        else:
            feed_back_to_pr(True,
                            "because pod that has been applied to test cluster is not alive, service is unreachable",
                            gee_token, org, repo, number)
            sys.exit(1)


if __name__ == '__main__':
    main()
