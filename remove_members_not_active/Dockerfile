FROM openeuler/openeuler:22.03-lts AS Builder

RUN yum update -y && yum install -y \
    python3 \
    python3-pip \
    wget \
    && pip3 install requests

WORKDIR /opt
RUN wget https://raw.githubusercontent.com/wanghao75/scripts/master/remove_members_not_active/remove_not_active_enterprise_members.py -O remove_not_active_enterprise_members.py

ENTRYPOINT ["python3", "remove_not_active_enterprise_members.py", "", "", ""]
