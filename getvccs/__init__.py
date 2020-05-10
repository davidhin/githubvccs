# %% Setup
import requests
import pandas as pd
import numpy as np
import json
import re

from github import Github
from whatthepatch import parse_patch

## Get blame from parent commit of given OID
def get_blame(reponame, oid, filepath, apitoken):
    url = 'https://api.github.com/graphql'
    reponame_split = reponame.split('/')
    owner = reponame_split[0]
    name = reponame_split[1]
    api_token = apitoken
    headers = {'Authorization': 'token %s' % api_token}
    
    # Get Parent Commit ID
    parentCommit = '''{{
        repository(name: "{}", owner: "{}") {{
            object(oid: "{}") {{
                ... on Commit {{
                        parents(first: 1) {{
                        edges {{
                            node {{
                                oid
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}'''.format(name, owner, oid)
    r = requests.post(url=url, json={'query': parentCommit}, headers=headers)
    res = json.loads(r.text)['data']['repository']['object']
    poid = res['parents']['edges'][0]['node']['oid']
    
    # Get blame for parent commit of file
    query = '''{{
        repository(name: "{}", owner: "{}") {{
            object(oid: "{}") {{
                ... on Commit {{
                    blame(path: "{}") {{
                        ranges {{
                            commit {{
                                id
                                message
                                committedDate
                                changedFiles
                                additions
                                deletions
                                commitUrl
                            }}
                            startingLine
                            endingLine
                        }}
                    }}
                }}
            }}
        }}
    }}'''.format(name, owner, poid, filepath)

    r = requests.post(url=url, json={'query': query}, headers=headers)
    res = json.loads(r.text)['data']['repository']['object']['blame']['ranges']
    return res

def get_potential_vccs(pygithub, apitoken, reponame, vfc_id):

    # Get repo
    repo = pygithub.get_repo(reponame)

    # Get changed files in vulerability fixing commit
    vfc = repo.get_commit(vfc_id)
    vfc_raw = vfc.raw_data
    vfc_files = vfc_raw['files']
    vfc_oid = vfc_raw['sha']

    # Get additions, deletions and replacements patch
    candidates = []    
    for f in vfc_files:

        # Parse patches and only keep added/removed/modified lines
        wtp = [i for i in parse_patch(f['patch'])][0].changes
        diffs = pd.DataFrame(wtp)
        rmdiffs = diffs[(diffs.new.isna()) | (diffs.old.isna())]

        # Skip if there are no removed or modified lines in file
        if (len(rmdiffs.old.dropna()) < 1): continue
        
        # Get blame of file on left side
        blame = get_blame(reponame, vfc_oid, f['filename'], apitoken)
        blamedf = pd.DataFrame(pd.json_normalize(blame))

        # Get commit associated with remove/modified line
        blame_commits = []
        for rline in rmdiffs.old.dropna().tolist():
            bcommit = blamedf[(blamedf.startingLine<=rline) & 
                              (blamedf.endingLine>=rline)]
            bcommit['old'] = rline
            blame_commits.append(bcommit)
                    
        blamecommitsdf = pd.concat(blame_commits).set_index('old')
        final = rmdiffs.set_index('old').join(blamecommitsdf).reset_index()
        
        # Set meta info and add to candidate info
        final['Filename'] = f['filename']
        final['Status'] = f['status']
        candidates.append(final)
        
    return pd.concat(candidates)
