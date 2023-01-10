import json
import os
import sys

import requests
import wget
import yaml


def clone_template_yamls(t: str):
    if os.path.exists("./kubectl-yaml-creator"):
        pwd = os.popen("pwd").readline()
        os.chdir("%s/kubectl-yaml-creator" % pwd.replace("\n", ""))
        os.system("git pull")
        os.chdir("../")
    else:
        os.system("git clone https://oauth2:%s@github.com/wanghao75/kubectl-yaml-creator.git" % t)


def load_checklist_yaml(org: str, repo: str, ge_token: str, pr_num: str):
    get_file_url = "https://gitee.com/api/v5/repos/{}/{}/pulls/{}/files".format(org, repo, pr_num)
    params = {
        "access_token": ge_token,
    }
    res = requests.get(url=get_file_url, params=params)

    if res.status_code != 200:
        print("can't get pr's files")
        sys.exit(1)

    for r in res.json():
        if r.get("filename").endswith("checklist.yaml"):
            link = r.get("raw_url")
            if os.path.exists("./checklists.yaml"):
                os.remove("./checklists.yaml")
            wget.download(link, "./checklists.yaml")
            with open("./checklists.yaml", "r", encoding="utf-8") as f:
                data = yaml.load(f.read(), Loader=yaml.SafeLoader)

    if len(data) == 0:
        print("checklist not in pr's changed files")
        sys.exit(1)

    return data


def complete_deployment_yaml(data):
    if os.path.exists("output/deployment.yaml"):
        os.remove("output/deployment.yaml")
    with open("kubectl-yaml-creator/demo/deployment.yaml", "r", encoding="utf-8") as f:
        with open("output/deployment.yaml", "a", encoding="utf-8") as f2:
            project_name = data.get("project")
            namespace = "deploy-workspace"
            replicas = data.get("replicas")
            containers = data.get("containers")
            volumes = data.get("volumes")

            deploy_template = yaml.load(f.read(), Loader=yaml.SafeLoader)
            deploy_template.get("metadata")["name"] = project_name
            deploy_template.get("metadata")["namespace"] = namespace
            deploy_template.get("spec")["replicas"] = replicas
            deploy_template.get("spec")["selector"]["matchLabels"]["app"] = project_name
            deploy_template.get("spec")["template"]["spec"]["containers"] = containers
            deploy_template.get("spec")["template"]["metadata"]["labels"]["app"] = project_name
            if volumes is not None:
                deploy_template.get("spec")["template"]["spec"]["volumes"] = volumes

            yaml.dump(deploy_template, f2)
    print("finish deploy")


def complete_pvc_yaml(data):
    if os.path.exists("output/pvc.yaml"):
        os.remove("output/pvc.yaml")
    init_pvc = False
    name = ""
    if data.get("volumes") is not None:
        for v in data.get("volumes"):
            if v.get("persistentVolumeClaim") is None:
                continue
            else:
                init_pvc = True
                name = v.get("persistentVolumeClaim").get("claimName")

    if not init_pvc:
        print("no need to init pvc.yaml")
        return

    storage = data.get("storage")
    storage_class_name = data.get("storageClassName")
    namespace = "deploy-workspace"

    with open("kubectl-yaml-creator/demo/pvc.yaml", "r", encoding="utf-8") as f:
        with open("output/pvc.yaml", "a", encoding="utf-8") as f2:
            pvc_template = yaml.load(f.read(), Loader=yaml.SafeLoader)
            pvc_template.get("metadata")["name"] = name
            pvc_template.get("metadata")["namespace"] = namespace
            pvc_template.get("spec")["resources"]["requests"]["storage"] = storage
            pvc_template.get("spec")["storageClassName"] = storage_class_name
            yaml.dump(pvc_template, f2)
    print("finish pvc")


def complete_ingress_yaml(data):
    if os.path.exists("output/ingress.yaml"):
        os.remove("output/ingress.yaml")
    if data.get("serviceExportType") != "Ingress":
        print("service doesn't need ingress.yaml")
        return

    ingress_name = data.get("project") + "-ingress"
    ingress_controller = data.get("ingress-controller")
    namespace = "deploy-workspace"
    secret_name = data.get("project") + "-tls"
    service_name = data.get("project") + "-service"
    domains = data.get("domain")
    rules = []
    for d in domains:
        host = {"host": d, "http": {
            "path": {
                "backend": {
                    "serviceName": "",
                    "servicePort": 80
                },
                "path": "/"
            }
        }}
        host["http"]["path"]["backend"]["serviceName"] = service_name
        rules.append(host)

    with open("kubectl-yaml-creator/demo/ingress.yaml", "r", encoding="utf-8") as f:
        with open("output/ingress.yaml", "a", encoding="utf-8") as f2:
            ingress_template = yaml.load(f.read(), Loader=yaml.SafeLoader)
            ingress_template.get("metadata")["name"] = ingress_name
            ingress_template.get("metadata")["annotations"]["kubernetes.io/ingress.class"] = ingress_controller
            ingress_template.get("metadata")["namespace"] = namespace
            ingress_template.get("spec")["tls"][0]["hosts"] = domains
            ingress_template.get("spec")["tls"][0]["secretName"] = secret_name
            ingress_template.get("spec")["rules"] = rules
            yaml.dump(ingress_template, f2)
    print("finish ingress")


def complete_secret_yaml(data):
    if os.path.exists("output/secret.yaml"):
        os.remove("output/secret.yaml")
    secret_name = data.get("project") + "-secret"
    namespace = "deploy-workspace"
    community = data.get("community")
    project = data.get("project")

    keysMap = []
    values = {}
    key_path = {"key": "", "path": ""}
    for c in data.get("containers"):
        if c.get("env") is not None:
            for e in c.get("env"):
                key = e.get("valueFrom")["secretKeyRef"]["key"]
                path = "secrets/data/{}/{}".format(community, project)
                key_path["key"] = key
                key_path["path"] = path
                values[key] = key_path
                keysMap.append(values)
                if e.get("valueFrom")["secretKeyRef"]["name"] != secret_name:
                    secret_name = e.get("valueFrom")["secretKeyRef"]["name"]

        if c.get("volumeMounts") is not None:
            for vv in c.get("volumeMounts"):
                if vv.get("subpath") is not None:
                    key = vv.get("subpath")
                    path = "secrets/data/{}/{}".format(community, project)
                    key_path["key"] = key
                    key_path["path"] = path
                    values[key] = key_path
                    keysMap.append(values)
    with open("kubectl-yaml-creator/demo/secret.yaml", "r", encoding="utf-8") as f:
        with open("output/secret.yaml", "a", encoding="utf-8") as f2:
            secret_template = yaml.load(f.read(), Loader=yaml.SafeLoader)
            secret_template.get("metadata")["name"] = secret_name
            secret_template.get("metadata")["namespace"] = namespace
            secret_template.get("spec")["name"] = secret_name
            secret_template.get("spec")["keysMap"] = keysMap
            yaml.dump(secret_template, f2)
    print("finish secret")


def complete_namespace_yaml(data):
    if os.path.exists("output/namespace.yaml"):
        os.remove("output/namespace.yaml")
    namespace = "deploy-workspace"
    with open("kubectl-yaml-creator/demo/namespace.yaml", "r", encoding="utf-8") as f:
        with open("output/namespace.yaml", "a", encoding="utf-8") as f2:
            namespace_template = yaml.load(f.read(), Loader=yaml.SafeLoader)
            namespace_template.get("metadata")["name"] = namespace
            namespace_template.get("metadata")["labels"]["name"] = namespace
            yaml.dump(namespace_template, f2)
    print("finish namespace")


def complete_kustomization_yaml(data):
    if os.path.exists("output/kustomization.yaml"):
        os.remove("output/kustomization.yaml")
    resource = []
    namespace = "deploy-workspace"
    files = os.listdir("output")
    for f in files:
        if f.endswith(".yaml"):
            resource.append(f)

    images_tags = []
    image_tag = {"name": "", "newTag": ""}

    for c in data.get("containers"):
        im = c.get("image")
        image = im.split(":")[0]
        tag = im.split(":")[1]
        image_tag["name"] = image
        image_tag["newTag"] = tag

        images_tags.append(image_tag)

    with open("kubectl-yaml-creator/demo/kustomization.yaml", "r", encoding="utf-8") as f:
        with open("output/kustomization.yaml", "a", encoding="utf-8") as f2:
            kustomization_template = yaml.load(f.read(), Loader=yaml.SafeLoader)
            kustomization_template["resources"] = resource
            kustomization_template["namespace"] = namespace
            kustomization_template["images"] = images_tags
            yaml.dump(kustomization_template, f2)
    print("finish kustomization")


def complete_service_yaml(data):
    if os.path.exists("output/service.yaml"):
        os.remove("output/service.yaml")
    service_name = data.get("project") + "-service"
    project = data.get("project")
    ports = []
    for c in data.get("containers"):
        for p in c.get("ports"):
            port = p.get("containerPort")
            port_json = {
                "name": "http-port",
                "protocol": "TCP",
                "port": 80,
                "targetPort": port,
            }
            ports.append(port_json)

    with open("kubectl-yaml-creator/demo/service.yaml", "r", encoding="utf-8") as f:
        with open("output/service.yaml", "a", encoding="utf-8") as f2:
            service_template = yaml.load(f.read(), Loader=yaml.SafeLoader)
            service_template.get("metadata")["name"] = service_name
            service_template.get("metadata")["namespace"] = project

            # because we got three types of service-type
            if data.get("serviceExportType") == "NodePort":
                service_template.get("spec")["type"] = data.get("serviceExportType")
                for p in ports:
                    if p.get("targetPort") == data.get("nodePort").split(":")[0]:
                        p["nodePort"] = data.get("nodePort")

            if data.get("serviceExportType") == "LoadBalancer":
                service_template.get("spec")["type"] = data.get("serviceExportType")

            if data.get("serviceExportType") == "Ingress":
                service_template.get("spec")["type"] = data.get("serviceExportType")

            else:
                service_template.get("spec")["type"] = "ClusterIP"

            service_template.get("spec")["ports"] = ports

            service_template.get("spec")["selector"]["app"] = project
            yaml.dump(service_template, f2)
    print("finish service")


def complete_configmap_yaml(data):
    if os.path.exists("output/configmap.yaml"):
        os.remove("output/configmap.yaml")

    if data.get("configMap") is None:
        print("no need to init configmap.yaml")
        return

    config_data = data.get("configMap").get("data")
    config_name = data.get("configMap").get("name")

    with open("output/configmap.yaml", "a", encoding="utf-8") as f:
        config = {}
        config["apiVersion"] = "v1"
        config["kind"] = "ConfigMap"
        config["metadata"] = {"name": config_name}
        config["data"] = config_data
        yaml.dump(config, f)
    print("finish configmap")


def complete_cronjob_yaml(data):
    if os.path.exists("output/cronjob.yaml"):
        os.remove("output/cronjob.yaml")
    container = data.get("containers")
    name = data.get("project")
    schedule = data.get("schedule")

    with open("output/cronjob.yaml", "a", encoding="utf-8") as f:
        cron = {}
        cron["apiVersion"] = "batch/v1beta1"
        cron["kind"] = "Cronjob"
        cron["metadata"] = {"name": name}
        cron["spec"] = {
            "schedule": schedule,
            "concurrencyPolicy": "Forbid",
            "jobTemplate": {"spec": {"template": {"spec": {"restartPolicy": "OnFailure", "containers": container}}}}
        }

        yaml.dump(cron, f)
    print("finish cronjob")


def all_init_yaml(data):
    os.system("mkdir output")
    if data.get("cronjob"):
        complete_cronjob_yaml(data)
        complete_secret_yaml(data)
        complete_kustomization_yaml(data)
    try:
        complete_deployment_yaml(data)
        complete_service_yaml(data)
        complete_secret_yaml(data)
        complete_ingress_yaml(data)
        complete_pvc_yaml(data)
        complete_namespace_yaml(data)
        complete_configmap_yaml(data)
        complete_kustomization_yaml(data)
    except Exception as e:
        print("init yaml failed ", e)
        sys.exit(1)


def check_yaml_valid():
    if os.path.exists("./deploy.yaml"):
        os.remove("./deploy.yaml")
    result = os.popen("./kustomize build output/ -o ./deploy.yaml")
    valid = True
    for res in result.readlines():
        if res.startswith("Error"):
            valid = False
            return valid

    return valid


def feed_back_to_pr(b: bool, og: str, rp: str, num: str, ge_token: str):
    if not b:
        gitee_api = "https://gitee.com/api/v5/repos/{}/{}/pulls/{}/comments".format(og, rp, num)
        data = {
            "access_token": ge_token,
            "body": "This checklist has something wrong, please check it."
                    "If you can not find out what's wrong, contact @githubliuyang777 to get some help."
        }
        requests.post(url=gitee_api, data=json.dumps(data))
    else:
        gitee_api2 = " https://gitee.com/api/v5/repos/{}/{}/pulls/{}/labels".format(og, rp, num)
        data = {
            "access_token": ge_token,
            "labels": ["yaml-check-pass"]
        }
        requests.post(url=gitee_api2, data=json.dumps(data))


def environment_injection(data):
    community = data.get("community")
    namespace = "deploy-workspace"
    project = data.get("project")
    os.system("setx /M COMMUNITY=%s" % community)
    os.system("setx /M POD_NAMESPACE=%s" % namespace)
    os.system("setx /M PROJECT=%s" % project)


def main():
    token = sys.argv[1]
    org = sys.argv[2]
    repo = sys.argv[3]
    number = sys.argv[4]
    gh_token = sys.argv[5]
    if len(sys.argv) != 6:
        print("missing args")
        sys.exit(1)

    # get template yaml files
    clone_template_yamls(gh_token)

    check_data = load_checklist_yaml(org, repo, token, number)
    all_init_yaml(check_data)

    # check valid yaml by kustomize build
    valid = check_yaml_valid()
    if valid:
        feed_back_to_pr(True, org, repo, number, token)
        environment_injection(check_data)
    else:
        feed_back_to_pr(False, org, repo, number, token)


if __name__ == '__main__':
    main()
