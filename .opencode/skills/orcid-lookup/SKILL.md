---
name: orcid-lookup
description: Use ORCID (https://orcid.org) to look up researchers by ORCID ID or name. Fetch their employment, education, funding, and publications with full metadata. Use ONLY when the user provides an ORCID ID (0000-0000-0000-0000 format), asks to find a researcher's ORCID, or wants publication lists by ORCID. NOT for general literature searches — use paper-search-pro or other academic skills for that.
---

# ORCID Lookup Skill

Use ORCID's public API to investigate researchers. No API key required.

## API Endpoints

| Endpoint | URL | Purpose |
|----------|-----|---------|
| Record | `https://pub.orcid.org/v3.0/{orcid}` | Full record (person, employment, education, funding, works, peer-review) |
| Search | `https://pub.orcid.org/v3.0/search/?q={query}` | Find ORCIDs by name/keyword |
| Expanded Search | `https://pub.orcid.org/v3.0/expanded-search/?q={query}` | Search with more result fields |
| CSV Search | `https://pub.orcid.org/v3.0/csv-search/search/?q={query}&fl=orcid,given-names,family-name,current-institution-affiliation-name` | Tabular output |

**Headers**: Always use `Accept: application/json` (or `application/vnd.orcid+json`).

## 1. Fetch a Full ORCID Record

```
curl -s -H "Accept: application/json" "https://pub.orcid.org/v3.0/0000-0002-1030-3721"
```

Extract key fields:

```python
import json, requests

data = requests.get(
    'https://pub.orcid.org/v3.0/0000-0002-1030-3721',
    headers={'Accept': 'application/json'}
).json()

# Person
name = data['person']['name']
given = name['given-names']['value']
family = name['family-name']['value']

# Employment
for aff in data['activities-summary']['employments']['employment-summary']:
    org = aff['organization']['name']
    dept = aff.get('department-name', '')
    role = aff.get('role-title', '')
    start = aff['start-date']
    end = aff.get('end-date')

# Education
for edu in data['activities-summary']['educations']['education-summary']:
    org = edu['organization']['name']
    dept = edu.get('department-name', '')
    role = edu.get('role-title', '')

# Works
for group in data['activities-summary']['works']['group']:
    work = group['work-summary'][0]
    title = work['title']['title']['value']
    pub_date = work.get('publication-date', {})
    year = pub_date.get('year', {}).get('value', '') if pub_date else ''
    doi = ''
    for ext_id in work.get('external-ids', {}).get('external-id', []):
        if ext_id['external-id-type'] == 'doi':
            doi = ext_id['external-id-value']
```

## 2. Search for a Researcher by Name

```
curl -s -H "Accept: application/json" "https://pub.orcid.org/v3.0/search/?q=given-names:Iain+AND+family-name:Dykes"
```

The search uses SOLR syntax. Supported fields:

| Field | Example |
|-------|---------|
| `given-names` | `given-names:John` |
| `family-name` | `family-name:Smith` |
| `credit-name` | `credit-name:"J. Smith"` |
| `current-institution-affiliation-name` | `current-institution-affiliation-name:"Liverpool John Moores"` |
| `past-institution-affiliation-name` | `past-institution-affiliation-name:Oxford` |
| `keyword` | `keyword:extracellular` |
| `text` (free text, all fields) | `text:extracellular+vesicles` |
| `orcid` | `orcid:0000-0002-1030-3721` |

Combine with `AND` / `OR`:

```
q=family-name:Ross+AND+current-institution-affiliation-name:"Liverpool John Moores"
```

## 3. Enrich Works with CrossRef

ORCID works often lack abstracts, citation counts, and full author lists. Enrich them via CrossRef's API using the DOI:

```
curl -s "https://api.crossref.org/v1/works/10.20517/evcna.2024.38"
```

Extract rich metadata:

```python
xref = requests.get(f'https://api.crossref.org/v1/works/{doi}').json()
msg = xref['message']

title = msg['title'][0]
authors = [f"{a['given']} {a['family']}" for a in msg.get('author', [])]
journal = msg.get('container-title', [''])[0]
year = msg.get('published-print', {}).get('date-parts', [[None]])[0][0] \
    or msg.get('published-online', {}).get('date-parts', [[None]])[0][0]
volume = msg.get('volume', '')
issue = msg.get('issue', '')
pages = msg.get('page', '')
doi = msg.get('DOI', '')
citations = msg.get('is-referenced-by-count', 0)
abstract = msg.get('abstract', '')
funders = [f['name'] for f in msg.get('funder', [])]
```

## 4. Find Researchers at an Institution

```
curl -s -H "Accept: application/json" \
  "https://pub.orcid.org/v3.0/search/?q=current-institution-affiliation-name:%22Liverpool+John+Moores%22&rows=100"
```

## 5. Expanded Search (name + institution in one call)

```
curl -s -H "Accept: application/json" \
  "https://pub.orcid.org/v3.0/expanded-search/?q=given-names:Kehinde+AND+family-name:Ross+AND+current-institution-affiliation-name:Liverpool"
```

Returns: `orcid-id`, `given-names`, `family-names`, `credit-name`, `other-name`, `email`, `institution-name`.

## 6. Search ORCID via OpenAlex (name → ORCID)

OpenAlex indexes ORCID-to-author mappings and provides a simpler name-search:

```
curl -s "https://api.openalex.org/authors?search=kehinde%20ross&filter=last_known_institutions.id:I90344687"
```

Extract ORCID:

```python
data = requests.get('https://api.openalex.org/authors?search=kehinde+ross').json()
for author in data.get('results', []):
    orcid = author.get('orcid')  # e.g. "0000-0002-xxxx-xxxx"
    name = author.get('display_name')
    institution = author['last_known_institutions'][0]['display_name'] if author.get('last_known_institutions') else ''
```

## 7. ORCID-to-OpenAlex Author ID

Get the OpenAlex ID for an ORCID holder (useful for citation metrics, co-authors):

```
curl -s "https://api.openalex.org/authors/orcid:0000-0002-1030-3721"
```

From the response you get: `h-index`, `i10-index`, `2yr_mean_citedness`, `works_count`, `cited_by_count`, `counts_by_year`.

## Complete Workflow Example

```python
import json, requests

def lookup_orcid(orcid):
    # Step 1: Fetch ORCID record
    resp = requests.get(
        f'https://pub.orcid.org/v3.0/{orcid}',
        headers={'Accept': 'application/json'}
    )
    data = resp.json()
    person = data['person']['name']
    result = {
        'name': f"{person['given-names']['value']} {person['family-name']['value']}",
        'employment': [],
        'education': [],
        'works': []
    }

    # Employment
    for aff in data['activities-summary']['employments']['employment-summary']:
        result['employment'].append({
            'org': aff['organization']['name'],
            'role': aff.get('role-title', ''),
            'dept': aff.get('department-name', ''),
            'start': f"{aff['start-date']['year']['value']}",
            'end': aff.get('end-date', {}).get('year', {}).get('value', 'present')
        })

    # Education
    for edu in data['activities-summary']['educations']['education-summary']:
        result['education'].append({
            'org': edu['organization']['name'],
            'role': edu.get('role-title', ''),
            'start': f"{edu['start-date']['year']['value']}",
            'end': edu.get('end-date', {}).get('year', {}).get('value', '')
        })

    # Works
    for group in data['activities-summary']['works']['group']:
        work = group['work-summary'][0]
        title = work['title']['title']['value']
        pub_date = work.get('publication-date', {})
        year = pub_date.get('year', {}).get('value', '') if pub_date else ''
        doi = ''
        for ext_id in work.get('external-ids', {}).get('external-id', []):
            if ext_id['external-id-type'] == 'doi':
                doi = ext_id['external-id-value']
        result['works'].append({'title': title, 'year': year, 'doi': doi})

    return result

def enrich_works_with_crossref(works):
    for w in works:
        if w['doi']:
            try:
                xref = requests.get(f"https://api.crossref.org/v1/works/{w['doi']}").json()['message']
                w['journal'] = xref.get('container-title', [''])[0]
                w['citations'] = xref.get('is-referenced-by-count', 0)
                w['authors'] = [f"{a.get('given','')} {a.get('family','')}" for a in xref.get('author', [])]
                w['abstract'] = (xref.get('abstract', '') or '')[:500]
            except:
                pass
    return works

def search_works_by_keyword(orcid, keyword):
    """Filter works containing keyword in title."""
    data = lookup_orcid(orcid)
    return [w for w in data['works'] if keyword.lower() in w['title'].lower()]
```
