# githubvccs

## Candidate VCCs

Set credentials ([obatining a personal token](https://github.blog/2013-05-16-personal-api-tokens/))
```python
g = Github("GITHUB_USERNAME", "GITHUB_PASSWORD")
APITOKEN = 'GITHUB_PERSONAL_ACCESS_TOKEN'
```

Get relevant patches and corresponding contributing commit
```python
get_potential_vccs(g,
                   APITOKEN,
                   'mantisbt-plugins/source-integration', 
                   '270675c964c675829fe010f9f0830521dc0835f0')
```

