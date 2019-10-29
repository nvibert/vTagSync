# import modules

import json
import requests                         # need this for Get/Post/Delete
import configparser                     # parsing config file

# customer settings. The customer needs to specify which ORG, SDDC and REFRESH TOKEN will be used.
config = configparser.ConfigParser()
config.read("./config.ini")
strProdURL      = config.get("vmcConfig", "strProdURL")
strCSPProdURL   = config.get("vmcConfig", "strCSPProdURL")
Refresh_Token   = config.get("vmcConfig", "refresh_Token")
ORG_ID          = config.get("vmcConfig", "org_id")
SDDC_ID         = config.get("vmcConfig", "sddc_id")

# Note that the refresh token has, by default, a 6-month lifespan. A token without expiration can also be created.

def lambda_handler(event, context):
    print("Received event: " + str(event))
    string_event = str(event)
    if string_event.find('attached tag') == -1:
        print(string_event.find('attached tag'))
        tag_name = ""
        indexToObject = string_event.find("from object")
        # tagged_VM below is the extract 'VM name' from the Log Intelligence event. We know that the name of the tagged VM is 12 characters after the beginning of 'from object' and finishes before ']'.
        tagged_VM = string_event[indexToObject + 12 : string_event.find("]", indexToObject)]
    else:
        print(string_event.find('attached tag'))
        # tag_name below is the extract 'tag' from the Log Intelligence event. We look for the string 'attached tag ' and look ahead 13 characters ahead to where the name of the tag is.
        tag_name = string_event[string_event.find('attached tag') + 13 : (string_event.find('to object') - 1)]
        indexToObject = string_event.find("to object")
        # tagged_VM below is the extract 'VM name' from the Log Intelligence event. We know that the name of the tagged VM is 10 characters after the beginning of 'to object' and finishes before ']'.
        tagged_VM = string_event[indexToObject + 10 : string_event.find("]", indexToObject)]
    print("The tag " + tag_name + " will be applied to " + tagged_VM + ".")
    # Following section requests a auth token from the refresh token via API and extracts it from the API JSON response.
    params = {'refresh_token': Refresh_Token}
    headers = {'Content-Type': 'application/json'}
    response = requests.post('https://console.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize', params=params, headers=headers)
    jsonResponse = response.json()
    access_token = jsonResponse['access_token']
    # Following section pulls the VM external_ID (also called VM InstanceUUID) based upon the name of the VM.
    myHeader = {'csp-auth-token': access_token}
    myURL = "{}/vmc/api/orgs/{}/sddcs/{}".format(strProdURL, ORG_ID, SDDC_ID)
    response = requests.get(myURL, headers=myHeader)
    json_response = response.json()
    proxy_url = json_response['resource_config']['nsx_api_public_endpoint_url']
    VMlist_url = (proxy_url + "/policy/api/v1/infra/realized-state/virtual-machines?enforcement_point_path=/infra/deployment-zones/default/enforcement-points/vmc-enforcementpoint")
    response = requests.get(VMlist_url, headers=myHeader)
    response_dictionary = response.json()
    extracted_dictionary = response_dictionary['results']
    # Below, we're extracting the Python dictionary for the specific VM and then we extract the external_ID/ Instance UUID from the dictionary.
    extracted_VM = next(item for item in extracted_dictionary if item["display_name"] == tagged_VM)
    extracted_VM_external_id = extracted_VM['external_id']
    # Finally, we're applying the NSX tag, using the External ID and tags.
    headers = {"Content-Type": "application/json","Accept": "application/json",'csp-auth-token': access_token}
    apply_tag_URL = (proxy_url + "/policy/api/v1/infra/realized-state/enforcement-points/vmc-enforcementpoint/virtual-machines?action=update_tags")
    json_data = {
    "virtual_machine_id": extracted_VM_external_id,
    "tags":[
      {
         "scope":"",
         "tag": tag_name
      }
   ]
   }
    response = requests.post(apply_tag_URL, json = json_data, params={'action': 'update_tags'}, headers=headers)
    print(tag_name)
    print(tagged_VM)
    print(apply_tag_URL)
    print(json_data)
    return apply_tag_URL, json_data, response.status_code

    
