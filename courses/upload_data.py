import sys
import json
import base64
import pathlib
import requests

import config


def login():
    try:
        headers = {'Content-Type': 'application/json'}
        data = {"mail": config.MAIL, "password": config.PASSWORD}
        res = requests.post(config.LOGIN_API, headers=headers, data=json.dumps(data))
        if res.status_code == 200:
            return res.json()['token']
        else:
            print('Authentication failed.')
            return None
    except:
        print('Authentication failed.')
        return None


def upload_image(auth_token, image, image_name):
    try:
        headers = {'Content-Type': 'application/json', 'X-CSRF-Token': auth_token}
        data = {
            "filename": image_name, "target_uri": f"public://{image_name}",
            "filemime": "image/jpeg", "file": image
        }
        res = requests.post(config.IMAGE_API, headers=headers, data=json.dumps(data))
        if res.status_code in [200, 201]:
            return res.json()['fid']
        else:
            print(f'Failure in uploading image {img_name}')
            return None
    except:
        print(f'Failure in uploading image {img_name}')
        return None


def create_course(auth_token, data):
    try:
        headers = {'Content-Type': 'application/json', 'X-CSRF-Token': auth_token}
        res = requests.post(config.COURSE_API, headers=headers, data=json.dumps(data))
        if res.status_code in [200, 201]:
            print(f'Successfully created course {res.json()}')
            return res.json()
        else:
            print(f'Failure in creating course with {data}')
            return None
    except:
        print(f'Failure in creating course with {data}')
        return None


if __name__ == '__main__':
    data_file_path = None
    try:
        data_file_path = sys.argv[1]
    except Exception as ex:
        print('Please provide json data file path as command line arg')
    token = login()
    if token:
        courses = json.load(open(data_file_path))
        for c in courses:
            img_count = 0
            for img in c['images']:
                try:
                    with open(f"{pathlib.Path(__file__).parent.absolute()}"
                              f"/courses/spiders/{img['path']}", 'rb') as img_file:
                        img_name = img['path'].split('full/')[1]
                        img_string = base64.b64encode(img_file.read()).decode('utf-8')
                        fid = upload_image(token, img_string, img_name)
                        if fid:
                            c['images_fids'].append(fid)
                except Exception as ex:
                    pass
                img_count += 1
                if img_count >= 5:
                    break
            create_course(token, c)


