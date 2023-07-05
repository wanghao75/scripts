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
        for branch in maps.get("openeuler/%s" % rp):
            os.popen("git checkout origin/%s" % branch).readlines()
            os.popen("git fetch upstream %s" % branch).readlines()
            os.popen("git merge upstream/%s" % branch).readlines()
            os.popen("git push origin HEAD:%s" % branch).readlines()

    for rp in src_openeuler_repos:
        os.chdir("/home/patches/src-openeuler/%s" % rp)
        for branch in maps.get("src-openeuler/%s" % rp):
            os.popen("git checkout origin/%s" % branch).readlines()
            os.popen("git fetch upstream %s" % branch).readlines()
            os.popen("git merge upstream/%s" % branch).readlines()
            os.popen("git push origin HEAD:%s" % branch).readlines()


def main():
    list_repos(load_configuration())
    
    
if __name__ == '__main__':
    main()
