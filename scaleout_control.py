#!/usr/bin/python
from avi.sdk.avi_api import ApiSession
import sys, json, logging, os
from time import sleep
from requests.packages import urllib3
urllib3.disable_warnings()


vs_dict= {}

def log(details):
    logging.basicConfig(format='%(asctime)s %(message)s', filename='/var/log/scale.log', level=logging.INFO,
                        datefmt='%m/%d/%Y-%H:%M:%S')
    logging.info(details)


def vs_info(tenant, version, scale_type='scaleout', vs_name=''):
    vs_query = '?name='+vs_name if vs_name else ''
    vs_output = session.get('virtualservice-inventory/'+vs_query, tenant=tenant, api_version=version, params={'page_size':1000})
    vs_json = json.loads(vs_output.text)
    for idx, vss in enumerate(vs_json['results']):
        vs_data = vs_json['results'][idx]
        type = vs_data['config']['type']
        if not type == 'VS_TYPE_VH_CHILD':
            try:
                enabled = vs_data['config']['enabled']
                if enabled:
                    vs_name = vs_data['config']['name']
                    vs_uuid = vs_data['config']['uuid']
                    vip_id = vs_data['runtime']['vip_summary'][0]['vip_id']
                    seg_ref = vs_data['config']['se_group_ref']
                    seg_uuid = seg_ref.split('/')[-1]
                    se_req = vs_data['runtime']['vip_summary'][0]['num_se_requested']
                    curr_se = vs_data['runtime']['vip_summary'][0]['num_se_assigned']
                    if scale_type == 'scalein' and se_req == 1:
                        continue
                    vs_dict[vs_name] = (vs_uuid, seg_uuid, vip_id, se_req, curr_se)

            except Exception as e:
                details = 'recieve the following error when retrieving the UUID for vs %s '%vs_name + e
                print details
                log(details)

def scale_info(version):
    scale_vs = {}
    seg_ses = {}
    seg_output = session.get('serviceenginegroup-inventory', api_version=version)
    seg_json = json.loads(seg_output.text)
    for idx, seg in enumerate(seg_json['results']):
        seg_uuid=seg_json['results'][idx]['uuid']
        seg_ses[seg_uuid] = len(seg_json['results'][idx]['serviceengines'])
    for vs in vs_dict:
        vs_uuid = vs_dict[vs][0]
        vs_seg = vs_dict[vs][1]
        vip_id = vs_dict[vs][2]
        se_req = vs_dict[vs][3]
        curr_se = vs_dict[vs][4]
        num_se = (seg_ses[vs_seg])
        if curr_se > 0 and se_req < num_se:
            scale_needed = num_se - se_req
            scale_vs[vs] = (vs_uuid, vip_id, scale_needed)
    return scale_vs



def scaleout_vs(vs, vs_uuid, vip_id, tenant):
    payload = '{"vip_id": "%s"}' %vip_id
    try:
        for tries in range(5):
            resp = session.post('virtualservice/%s/scaleout' %vs_uuid, data=payload, tenant=tenant)
            if resp.status_code == 200:
                print vs, 'scaled out successfully'
                log('%s scaled out successfully'%vs)
                return
            else:
                details = vs+': '+str(resp.status_code)+' '+resp.text
                print details
                log(details)
                print 'retrying...'
                sleep(10)
        log('unable to scaleout vs %s' %vs)
    except Exception as e:
        log(e)


if __name__ == '__main__':
    alert = json.loads(sys.argv[1])
    vs_data = alert['events'][0]
    vs_uuid = vs_data['obj_uuid']
    vs_name = vs_data['obj_name']
    log(vs_name + ' created, attempting to scale')
    token = os.environ.get('API_TOKEN')
    user = os.environ.get('USER')
    tenant=os.environ.get('TENANT')
    session = ApiSession.get_session("localhost", user, token=token, tenant=tenant)
    version='17.2.7'
    vs_info(tenant, version, vs_name=vs_name)
    scale_vs = scale_info(version)
    num = len(scale_vs)
    if num > 0:
        for vs in scale_vs:
            vs_scale = scale_vs[vs][2]
            log("attempting to scale %s to %s SE's" %(vs, vs_scale))
    else:
        log("All VS's are currently scaled out to max # of SE's")
        sys.exit(0)
    count = 1
    while scale_vs:
        for vs in list(scale_vs):
            scaleout_vs(vs, scale_vs[vs][0], scale_vs[vs][1], tenant)
            if scale_vs[vs][2] - count <= 0:
                del scale_vs[vs]
        count += 1
        sleep(5)