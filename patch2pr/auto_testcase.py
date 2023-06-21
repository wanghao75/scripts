import os
import re
import unittest
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
        os.popen("rm -f *.patch && git pull").readlines()
        test_branch = "case-%d" % int(time.time())
        os.popen("git checkout -b %s origin/%s" % (test_branch, branch)).readlines()
        cherry_result = os.popen("git cherry-pick --abort;git cherry-pick %s -s" % tag).readlines()
        stop = False
        for r in cherry_result:
            if "Merge conflict" in r or "git cherry-pick --skip" in r:
                stop = True
                break
        patch_num = 0
        if stop:
            status = os.popen("git status").readlines()
            mc = re.compile(r'(by )\d+( commits)')
            for s in status:
                if mc.search(s):
                    patch_num = s.split("by")[1].split("commits")[0].strip(" ")
                    break

        if patch_num == 0:
            return complete

        os.popen('git format-patch -%d --subject-prefix="PATCH %s"' % (patch_num, branch))
        os.popen('git send-email *.patch --to "%s" --cc "%s" --suppress-cc=all' % (to_list, cc_list)).readlines()
        os.popen("git cherry-pick --abort")
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
        os.popen("rm -f *.patch && git pull").readlines()
        test_branch = "case-%d" % int(time.time())
        os.popen("git checkout -b %s origin/%s" % (test_branch, branch)).readlines()
        cherry_result = os.popen("git cherry-pick --abort;git cherry-pick %s -s" % tag).readlines()
        stop = False
        for r in cherry_result:
            if "Merge conflict" in r or "git cherry-pick --skip" in r:
                stop = True
                break
        patch_num = 0
        if stop:
            status = os.popen("git status").readlines()
            mc = re.compile(r'(by )\d+( commits)')
            for s in status:
                if mc.search(s):
                    patch_num = s.split("by")[1].split("commits")[0].strip(" ")
                    break

        if patch_num == 0:
            return complete

        if version == "":
            os.popen('git format-patch -%d --subject-prefix="PATCH %s" --cover-letter' % (patch_num, branch))
        else:
            os.popen('git format-patch -%d --subject-prefix="PATCH %s %s" --cover-letter' % (patch_num, version, branch))
        os.popen('git send-email *.patch --to "%s" --cc "%s" --suppress-cc=all' % (to_list, cc_list)).readlines()
        os.popen("git cherry-pick --abort")
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
        os.popen("rm -f *.patch && git pull").readlines()
        test_branch = "case-%d" % int(time.time())
        os.popen("git checkout -b %s origin/%s" % (test_branch, branch)).readlines()
        cherry_result = os.popen("git cherry-pick --abort;git cherry-pick %s -s" % tag).readlines()
        stop = False
        for r in cherry_result:
            if "Merge conflict" in r or "git cherry-pick --skip" in r:
                stop = True
                break
        patch_num = 0
        if stop:
            status = os.popen("git status").readlines()
            mc = re.compile(r'(by )\d+( commits)')
            for s in status:
                if mc.search(s):
                    patch_num = s.split("by")[1].split("commits")[0].strip(" ")
                    break

        if patch_num == 0:
            return complete

        os.popen('git format-patch -%d --subject-prefix="PATCH %s" --cover-letter' % (patch_num, branch))
        l = os.popen("ls").readlines()
        for num, ll in enumerate(l):
            if ll.strip("\n").endswith(".patch"):
                os.popen('git send-email %s --to "%s" --cc "%s" --suppress-cc=all' %
                         (ll.strip("\n"), to_list, cc_list)).readlines()
                if num >= 3:
                    break
        os.popen("git cherry-pick --abort")
        complete = True

        return complete

    def case_4(self, to_list: str, cc_list: str):
        os.chdir("/root/linux-git/k1")
        os.popen('git send-email *.patch --to "%s" --cc "%s" --suppress-cc=all' % (to_list, cc_list))
        return True


class AutoTest(unittest.TestCase):

    def setUp(self) -> None:
        self.test_case = Test()

    # same patch(es), one have a cover, another don't have
    def test_case_1(self):
        self.assertTrue(self.test_case.case_1(
            "wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
            "openEuler-22.03-LTS-SP2", "v5.10.170..v5.10.171~1"), True)

    def test_case_2(self):
        self.assertTrue(self.test_case.case_2(
            "wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
            "openEuler-22.03-LTS-SP2", "v5.10.170..v5.10.171~1", ""), True)

    # do not send all patches, test retry 3 times, then drop ths patch(es)
    def test_case_3(self):
        self.assertTrue(self.test_case.case_3(
            "wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
            "openEuler-22.03-LTS-SP1", "v5.10.163..v5.10.164~1"), True)

    # another way to provide the email address
    def test_case_4(self):
        self.assertTrue(self.test_case.case_2(
            "2467577789@qq.com,wanghaosqsq@163.com", "wanghaosqsq@gmail.com",
            "openEuler-22.03-LTS-SP2", "v5.10.173..v5.10.174~1", ""), True)

    # patch(es) with version
    def test_case_5(self):
        self.assertTrue(self.test_case.case_2(
            "wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
            "openEuler-22.03-LTS", "v5.10.170..v5.10.171~1", "v2"), True)

    # apply patch failed because of patch is wrong
    def test_case_6(self):
        self.assertTrue(self.test_case.case_4(
            "wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",), True)

    # illegal branch
    def test_case_7(self):
        self.assertTrue(self.test_case.case_2(
            "wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
            "openEuler-1.0-LTS", "v5.10.173..v5.10.174~1", ""), True)

    # a big series of patches
    def test_case_8(self):
        self.assertTrue(self.test_case.case_2(
            "wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>", "W H <wanghaosqsq@gmail.com>",
            "openEuler-22.03-LTS", "v5.10.172..v5.10.173~1", ""), True)

    #
    def test_case_9(self):
        pass

    def tearDown(self) -> None:
        del self.test_case


if __name__ == '__main__':
    unittest.main()
