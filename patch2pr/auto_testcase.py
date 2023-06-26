import os
import re
import time


class Test(object):

    def case_1(self, to_list: str, cc_list: str, branch: str,  tag: str):
        """
        test patch with no cover to the regular mailing list
        :param to_list: email
        :param cc_list: email
        :param branch: source branch
        :param tag: a tag of code which is using by cherry-pick
        :return: bool
        """
        complete = False
        os.chdir("/root/linux-git/kernel")
        os.popen("rm -f *.patch").readlines()
        test_branch = "case-%d" % int(time.time())
        os.popen("git checkout -f -b %s origin/%s" % (test_branch, branch)).readlines()
        os.popen("git cherry-pick --abort").readlines()
        cherry_result = os.popen("git cherry-pick %s -s" % tag).readlines()
        stop = False
        for r in cherry_result:
            if "Merge conflict" in r or "git cherry-pick --skip" in r:
                stop = True
                break
        patch_num = 0
        if stop:
            status = os.popen("git status").readlines()
            mc = re.compile(r'(by )\d+( commits)')
            mc2 = re.compile(r'(by )\d+( commit)')
            for s in status:
                if mc.search(s):
                    patch_num = int(s.split("by")[1].split("commits")[0].strip(" "))
                    break
                if mc2.search(s):
                    patch_num = int(s.split("by")[1].split("commit")[0].strip(" "))
                    break

        if patch_num == 0:
            return complete

        os.popen('git format-patch -%d --subject-prefix="PATCH %s"' % (patch_num, branch)).readlines()
        os.popen('git send-email *.patch --to "%s" --cc "%s" --suppress-cc=all --force' %
                 (to_list, cc_list)).readlines()
        os.popen("git cherry-pick --abort").readlines()
        complete = True

        return complete

    def case_2(self, to_list: str, cc_list: str, branch: str,  tag: str, version: str):
        """
        test patch with a cover to the regular mailing list
        :param to_list: email
        :param cc_list: email
        :param branch: source branch
        :param tag: a tag of code which is using by cherry-pick
        :param version: version, like v2
        :return: bool
        """
        complete = False
        os.chdir("/root/linux-git/kernel")
        os.popen("rm -f *.patch").readlines()
        test_branch = "case-%d" % int(time.time())
        os.popen("git checkout -f -b %s origin/%s" % (test_branch, branch)).readlines()
        os.popen("git cherry-pick --abort").readlines()
        cherry_result = os.popen("git cherry-pick %s -s" % tag).readlines()
        stop = False
        for r in cherry_result:
            if "Merge conflict" in r or "git cherry-pick --skip" in r:
                stop = True
                break
        patch_num = 0
        if stop:
            status = os.popen("git status").readlines()
            mc = re.compile(r'(by )\d+( commits)')
            mc2 = re.compile(r'(by )\d+( commit)')
            for s in status:
                if mc.search(s):
                    patch_num = int(s.split("by")[1].split("commits")[0].strip(" "))
                    break
                if mc2.search(s):
                    patch_num = int(s.split("by")[1].split("commit")[0].strip(" "))
                    break

        if patch_num == 0:
            return complete

        if version == "":
            os.popen('git format-patch -%d --subject-prefix="PATCH %s" --cover-letter' % (patch_num, branch)).readlines()
        else:
            os.popen('git format-patch -%d --subject-prefix="PATCH %s %s" --cover-letter' % 
                     (patch_num, version, branch)).readlines()
        os.popen('git send-email *.patch --to "%s" --cc "%s" --suppress-cc=all --force' % (to_list, cc_list)).readlines()
        os.popen("git cherry-pick --abort").readlines()
        complete = True

        return complete

    def case_3(self, to_list: str, cc_list: str, branch: str,  tag: str):
        """
        test patch with a cover to the regular mailing list, but not send all
        :param to_list: email
        :param cc_list: email
        :param branch: source branch
        :param tag: a tag of code which is using by cherry-pick
        :return: bool
        """
        complete = False
        os.chdir("/root/linux-git/kernel")
        os.popen("rm -f *.patch").readlines()
        test_branch = "case-%d" % int(time.time())
        os.popen("git checkout -f -b %s origin/%s" % (test_branch, branch)).readlines()
        os.popen("git cherry-pick --abort").readlines()
        cherry_result = os.popen("git cherry-pick %s -s" % tag).readlines()
        stop = False
        for r in cherry_result:
            if "Merge conflict" in r or "git cherry-pick --skip" in r:
                stop = True
                break
        patch_num = 0
        if stop:
            status = os.popen("git status").readlines()
            mc = re.compile(r'(by )\d+( commits)')
            mc2 = re.compile(r'(by )\d+( commit)')
            for s in status:
                if mc.search(s):
                    patch_num = int(s.split("by")[1].split("commits")[0].strip(" "))
                    break
                if mc2.search(s):
                    patch_num = int(s.split("by")[1].split("commit")[0].strip(" "))
                    break

        if patch_num == 0:
            return complete

        os.popen('git format-patch -%d --subject-prefix="PATCH %s" --cover-letter' % (patch_num, branch)).readlines()
        l = os.popen("ls").readlines()
        for num, ll in enumerate(l):
            if ll.strip("\n").endswith(".patch"):
                os.popen('git send-email %s --to "%s" --cc "%s" --suppress-cc=all --force' %
                         (ll.strip("\n"), to_list, cc_list)).readlines()
                if num >= 3:
                    break
        os.popen("git cherry-pick --abort").readlines()
        complete = True

        return complete

    def case_4(self, to_list: str, cc_list: str):
        os.chdir("/root/linux-git/k1")
        os.popen('git send-email *.patch --to "%s" --cc "%s" --suppress-cc=all --force' %
                 (to_list, cc_list)).readlines()
        return True


def main():
    t = Test()

    # same patch(es), one have a cover, another don't have
    pass1 = t.case_1("wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
                     "openEuler-22.03-LTS-SP2", "v5.10.170..v5.10.171~1")

    if not pass1:
        print("case1 failed")

    pass2 = t.case_2("wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
                     "openEuler-22.03-LTS-SP2", "v5.10.170..v5.10.171~1", "")

    if not pass2:
        print("case2 failed")

    # do not send all patches, test retry 3 times, then drop ths patch(es)
    pass3 = t.case_3("wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
                     "openEuler-22.03-LTS-SP1", "v5.10.163..v5.10.164~1")

    if not pass3:
        print("case3 failed")

    # another way to provide the email address
    pass4 = t.case_2("2467577789@qq.com,wanghaosqsq@163.com", "wanghaosqsq@gmail.com",
                     "openEuler-22.03-LTS-SP2", "v5.10.173..v5.10.174~1", "")

    if not pass4:
        print("case4 failed")

    # patch(es) with version
    pass5 = t.case_2("wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
                     "openEuler-22.03-LTS", "v5.10.170..v5.10.171~1", "v2")
    if not pass5:
        print("case5 failed")

    # apply patch failed because of patch is wrong
    pass6 = t.case_4("wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",)
    if not pass6:
        print("case6 failed")

    # illegal branch
    pass7 = t.case_2("wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
                     "openEuler-1.0-LTS", "v5.10.173..v5.10.174~1", "")
    if not pass7:
        print("case7 failed")

    # a big series of patches (simple one)
    pass8 = t.case_2("wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
                     "openEuler-22.03-LTS", "v5.10.176..v5.10.177~1", "")
    if not pass8:
        print("case8 failed")


if __name__ == '__main__':
    main()
