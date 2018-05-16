from avi.sdk.avi_api import ApiSession
import argparse, sys, json, logging
from time import sleep
from requests.packages import urllib3
urllib3.disable_warnings()

vs_dict = {}

def log(details):
    logging.basicConfig(format='%(asctime)s %(message)s', filename='scale.log', level=logging.INFO,
                        datefmt='%m/%d/%Y-%H:%M:%S')
    logging.info(details)


def vs_info(session, tenant, version, scale_type='scaleout', vs_name=''):
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
        num_se = (seg_ses[vs_seg])/2
        if curr_se > 0 and se_req < num_se:
            scale_needed = num_se - se_req
            scale_vs[vs] = (vs_uuid, vip_id, scale_needed)
    return scale_vs

def confirm(num, scale_type='scaleout'):
    proceed = raw_input('%s %d virtualservice(s)?, y/n: ' %(scale_type, num))
    attempts = 0
    while not proceed.lower() == 'y':
        if proceed.lower() == 'n' or attempts == 3:
            sys.exit(0)
        else:
            proceed = input('would you like to proceed, y/n: ')
            attempts +=1
    return



def scaleout_vs(vs, vs_uuid, vip_id, tenant):
    payload = '{"vip_id": "%s"}' %vip_id
    try:
        for tries in range(3):
            resp = session.post('virtualservice/%s/scaleout' %vs_uuid, data=payload, tenant=tenant)
            if resp.status_code == 200:
                print vs, 'VS scaled out successfully'
                return
            else:
                details = vs+': '+str(resp.status_code)+' '+resp.text
                print details
                log(details)
                print 'retrying...'
                sleep(60)
        print 'unable to scaleout vs', vs
        log('unable to scaleout vs %s' %vs)
    except Exception as e:
        log(e)

def scalein_vs(vs, vs_uuid, vip_id, tenant):
    payload = '{"vip_id": "%s"}' %vip_id
    try:
        for tries in range(3):
            resp = session.post('virtualservice/%s/scalein' %vs_uuid, data=payload, tenant=tenant)
            if resp.status_code == 200:
                print vs, 'VS scaled in successfully'
                return
            else:
                details = vs+': '+str(resp.status_code) +' '+ resp.text
                print details
                log(details)
                print 'retrying...'
                sleep(60)
        print 'unable to scalein vs', vs
    except Exception as e:
        log(e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--tenant', default='admin')
    parser.add_argument('--token', default='')
    parser.add_argument('-u', '--user', default='admin')
    parser.add_argument('-p', '--passwd')
    parser.add_argument('-c', '--ctlr')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--version', default='17.2.7')
    parser.add_argument('--scalein', action='store_true')
    parser.add_argument('-f', '--force',  action='store_true')
    parser.add_argument('-P', '--plan', action='store_true')
    parser.add_argument('-V', '--virtualservice', default='')

    args = parser.parse_args()

    session = ApiSession.get_session(args.ctlr, args.user, args.passwd, api_version=args.version, token=args.token, tenant=args.tenant)
    if args.scalein:a
        vs_info(session, args.tenant, args.version, 'scalein', args.virtualservice)
        num = len(vs_dict)
        if num:
            print '%s virtualservices will be scaled in' %num
        else:
            print 'no virtual services to scale in'
            sys.exit(0)
        if args.verbose:
            for vs in vs_dict:
                print vs
        if not args.plan:
            if not args.force:
                confirm(num, 'scalein')
        for idx, vs in enumerate(vs_dict):
            vs_uuid = vs_dict[vs][0]
            vip_id = vs_dict[vs][2]
            print num-idx,
            scalein_vs(vs, vs_uuid, vip_id, args.tenant)

    else:
        vs_info(session, args.tenant, args.version, vs_name=args.virtualservice)
        scale_vs = scale_info(args.version)
        num = len(scale_vs)
        if  num > 0:
            print '%s virtualservices will be scaled out' %num
            for vs in scale_vs:
                vs_scale = scale_vs[vs][2]
                if args.verbose:
                    print vs + ':', '(x%d)'%vs_scale
        else:
            print "All VS's are currently scaled out to max # of SE's"
            sys.exit(0)
        if not args.plan:
            if not args.force:
                confirm(num)

            count = 1
            while scale_vs:
                for idx, vs in enumerate(list(scale_vs)):
                    print num-idx,
                    scaleout_vs(vs, scale_vs[vs][0],scale_vs[vs][1], args.tenant)
                    if scale_vs[vs][2] - count <= 0:
                        del scale_vs[vs]
                print 'allowing scaleout to complete'
                count+=1
                sleep(5)







