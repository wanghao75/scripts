import os
import yaml


def load_configuration():
    m = {}
    with open('/home/patches/repositories_branches_map.yaml', "r", encoding="utf-8") as f:
        d = yaml.safe_load(f.read())

    for k, v in d.get("mapping").items():
        m[k] = v.get("branches")
    return m


def list_repos(maps: dict):
    openeuler_repos = []
    r1 = os.popen("ls /home/patches/openeuler").readlines()
    for i in r1:
        openeuler_repos.append(i.split("\n")[0])
    src_openeuler_repos = []
    r1 = os.popen("ls /home/patches/src-openeuler").readlines()
    for i in r1:
        src_openeuler_repos.append(i.split("\n")[0])

    for rp in openeuler_repos:
        os.chdir("/home/patches/openeuler/%s" % rp)
        exists_branches = []
        cmd_res = os.popen("git branch -a").readlines()
        for i in cmd_res:
            exists_branches.append(i.strip(" ").strip("\n"))
        
        for branch in maps.get("openeuler/%s" % rp):
            if branch not in exists_branches and "remotes/origin/%s" % branch not in exists_branches and \
                    "remotes/upstream/%s" % branch not in exists_branches:
                os.popen("git fetch upstream %s" % branch).readlines()
                os.popen("git checkout -b %s upstream/%s" % (branch, branch)).readlines()
                os.popen("git push -u origin %s" % branch).readlines()
            else:
                os.popen("git checkout origin/%s" % branch).readlines()
                os.popen("git fetch upstream %s" % branch).readlines()
                os.popen("git merge upstream/%s" % branch).readlines()
                os.popen("git push origin HEAD:%s" % branch).readlines()

    for rp in src_openeuler_repos:
        os.chdir("/home/patches/openeuler/%s" % rp)
        exists_branches = []
        cmd_res = os.popen("git branch -a").readlines()
        for i in cmd_res:
            exists_branches.append(i.strip(" ").strip("\n"))
            
        for branch in maps.get("src-openeuler/%s" % rp):
            if branch not in exists_branches and "remotes/origin/%s" % branch not in exists_branches and \
                    "remotes/upstream/%s" % branch not in exists_branches:
                os.popen("git fetch upstream %s" % branch).readlines()
                os.popen("git checkout -b %s upstream/%s" % (branch, branch)).readlines()
                os.popen("git push -u origin %s" % branch).readlines()
            else:
                os.popen("git checkout origin/%s" % branch).readlines()
                os.popen("git fetch upstream %s" % branch).readlines()
                os.popen("git merge upstream/%s" % branch).readlines()
                os.popen("git push origin HEAD:%s" % branch).readlines()


def main():
    list_repos(load_configuration())


if __name__ == '__main__':
    main()
