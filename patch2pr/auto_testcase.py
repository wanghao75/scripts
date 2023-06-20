import os
import re
import unittest
import time


class Test(object):

    def case_1(self, to_list: str, cc_list: str, branch: str,  tag: str):
        """
        test a single patch with no cover to the regular mailing list
        :param to_list: email
        :param cc_list: email
        :param branch: source branch
        :param tag: a tag of code which is using by cherry-pick
        :return: bool
        """
        complete = False
        os.popen("cd /root/linux-git/kernel && git pull").readlines()
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

        os.popen('git format-patch -%d --subject-prefix="PATCH %s" --cover-letter' % (patch_num, branch))
        os.popen('git send-email *.patch --to %s --cc %s --suppress-cc=all').readlines()
        complete = True

        return complete


class AutoTest(unittest.TestCase):

    def setUp(self) -> None:
        self.test_case = Test()

    def test_case_1(self):
        self.test_case.case_1("wang hao <2467577789@qq.com>,WANG QIAN <wanghaosqsq@163.com>",
                              "W H <wanghaosqsq@gmail.com>", "openEuler-22.03-LTS-SP2", "v5.10.170..v5.10.171~1")

    def tearDown(self) -> None:
        del self.test_case


if __name__ == '__main__':
    unittest.main()
