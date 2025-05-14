import requests
import re
import subprocess
import time
from data import headers # must get your own headers from incognito

def run_warp():
    subprocess.run(
        ["warp-cli", "disconnect"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    subprocess.run(
        ["warp-cli", "connect"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    while True:
        result = subprocess.run(["warp-cli", "status"], capture_output=True, text=True)
        if "Connected" in result.stdout:
            break
        time.sleep(1)

def get_jobs():
    jobs = []
    url = "https://www.upwork.com/api/graphql/v1?alias=visitorJobSearch"

    payload = "{\"query\":\"\\n  query VisitorJobSearch($requestVariables: VisitorJobSearchV1Request!) {\\n    search {\\n      universalSearchNuxt {\\n        visitorJobSearchV1(request: $requestVariables) {\\n          paging {\\n            total\\n            offset\\n            count\\n          }\\n          \\n    facets {\\n      jobType \\n    {\\n      key\\n      value\\n    }\\n  \\n      workload \\n    {\\n      key\\n      value\\n    }\\n  \\n      clientHires \\n    {\\n      key\\n      value\\n    }\\n  \\n      durationV3 \\n    {\\n      key\\n      value\\n    }\\n  \\n      amount \\n    {\\n      key\\n      value\\n    }\\n  \\n      contractorTier \\n    {\\n      key\\n      value\\n    }\\n  \\n      contractToHire \\n    {\\n      key\\n      value\\n    }\\n  \\n      \\n    }\\n  \\n          results {\\n            id\\n            title\\n            description\\n            relevanceEncoded\\n            ontologySkills {\\n              uid\\n              parentSkillUid\\n              prefLabel\\n              prettyName: prefLabel\\n              freeText\\n              highlighted\\n            }\\n            \\n            jobTile {\\n              job {\\n                id\\n                ciphertext: cipherText\\n                jobType\\n                weeklyRetainerBudget\\n                hourlyBudgetMax\\n                hourlyBudgetMin\\n                hourlyEngagementType\\n                contractorTier\\n                sourcingTimestamp\\n                createTime\\n                publishTime\\n                \\n                hourlyEngagementDuration {\\n                  rid\\n                  label\\n                  weeks\\n                  mtime\\n                  ctime\\n                }\\n                fixedPriceAmount {\\n                  isoCurrencyCode\\n                  amount\\n                }\\n                fixedPriceEngagementDuration {\\n                  id\\n                  rid\\n                  label\\n                  weeks\\n                  ctime\\n                  mtime\\n                }\\n              }\\n            }\\n          }\\n        }\\n      }\\n    }\\n  }\\n  \",\"variables\":{\"requestVariables\":{\"userQuery\":\"(automation OR python OR automate OR bot OR spreadsheet OR scrap OR api)\",\"sort\":\"recency\",\"highlight\":false,\"paging\":{\"offset\":0,\"count\":50}}}}"
    
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        data = response.json()
        data = data['data']['search']['universalSearchNuxt']['visitorJobSearchV1']['results']
    except Exception:
        run_warp()
        response = requests.request("POST", url, headers=headers, data=payload)
        data = response.json()
        data = data['data']['search']['universalSearchNuxt']['visitorJobSearchV1']['results']
    for x in data:
        jobdata = x['jobTile']['job']
        title = x['title']
        description = x['description']
        type = jobdata['jobType'].title()
        experience_level = jobdata['contractorTier']
        experience_level = re.sub(r'(?<!^)(?=[A-Z])', ' ', experience_level)
        id = jobdata['ciphertext']
        link = f"https://www.upwork.com/jobs/{id}"
        if type == "Fixed":
            price = jobdata['fixedPriceAmount']['amount']
        else:
            min = jobdata['hourlyBudgetMin']
            max = jobdata['hourlyBudgetMax']
            price = f'${min}-${max}'
            if min == None and max == None:
                price = 'Not specified'
        data = {
            'id': id[1:],
            'title': title,
            'description': description,
            'link': link,
            'type': type,
            'price': price,
            'experience_level': experience_level
            }
        
        jobs.append(data)
    return jobs 
