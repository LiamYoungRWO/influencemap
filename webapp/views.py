import os, sys, json, pandas, string
import multiprocess
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import datetime
from collections import Counter
from operator import itemgetter
from webapp.graph import processdata
from webapp.elastic import search_cache, query_conference_series, query_journal, query_affiliation
from webapp.utils import *

import core.utils.entity_type as ent
from core.search.parse_academic_search import parse_search_results
from core.search.academic_search import *
from core.flower.draw_flower_test import draw_flower
from core.flower.flower_bloomer import getFlower, getPreFlowerData
from core.search.mag_flower_bloom import *
from core.utils.get_entity import entity_from_name
from core.search.influence_df import get_filtered_score
from core.search.search import search_name
from graph.save_cache import *
from core.utils.load_tsv import tsv_to_dict

from core.flower.high_level_get_flower import gen_flower_data
from core.flower.high_level_get_flower import default_config
from core.score.agg_paper_info         import score_paper_info_list

# Imports for submit
from core.search.query_paper    import paper_query
from core.search.query_info     import paper_info_check_query, paper_info_mag_check_multiquery
from core.search.query_info_mag import base_paper_mag_multiquery
from core.score.agg_utils       import get_coauthor_mapping
from core.score.agg_utils       import flag_coauthor
from core.utils.get_stats       import get_stats

BASE_DIR = settings.BASE_DIR

flower_leaves = [ ('author', [ent.Entity_type.AUTH])
                , ('conf'  , [ent.Entity_type.CONF, ent.Entity_type.JOUR])
                , ('inst'  , [ent.Entity_type.AFFI]) ]

NUM_THREADS = 8

def autocomplete(request):
    entity_type = request.GET.get('option')
    data = loadList(entity_type)
    return JsonResponse(data,safe=False)

@csrf_exempt
def main(request):
    return render(request, "main.html")

@csrf_exempt
def browse(request):

    which = request.GET.get("which")
    if which and which=="sigmm":
        browse_file = "webapp/static/sigmm_browse_lists.json"
    else:
        browse_file = "webapp/static/browse_lists.json"
    browse_list_filename = os.path.join(BASE_DIR, browse_file)
    with open(browse_list_filename, 'r') as fp:
        browse_list = json.load(fp)

    for entity in browse_list:
        res = search_cache(entity["cache_index"], entity["cache_type"])
        entity["names"] = list(set([n["DisplayName"] for n in res]))
        entity["entities"] = res

        for i in range(len(entity["entities"])):
            e = entity["entities"][i]
            document_id = e["_id"]
            e["document_id"] = document_id
            if "Keywords" in e:
                e["Keywords"] = [] if len("".join(e["Keywords"])) == 0 else e["Keywords"]
            if "AuthorIds" in e:
                e["AuthorIds"] = json.dumps(e["AuthorIds"])
            if "NormalizedNames" in e:
                e["NormalizedName"] = e["NormalizedNames"][0]
            e['CacheIndex'] = entity["cache_index"]
            entity["entities"][i] = e

    data = {
        'list': browse_list,
        "navbarOption": get_navbar_option()
    }
    return render(request, "browse.html", data)


@csrf_exempt
def create(request):
    print(request)

    try:
        data = json.loads(request.POST.get('data'))
        keyword = data.get('keyword', '')
        search = data.get('search') == 'true'
        option = data.get('option')
    except:
        keyword = ""
        option = ""
        search = False

    print(search)
    # render page with data
    return render(request, "create.html", {
        "navbarOption": get_navbar_option(keyword, option),
        "search": search
    })



@csrf_exempt
def curate(request):
    print(request)

    try:
        data = json.loads(request.POST.get('data'))
        keyword = data.get('keyword', '')
        search = data.get('search') == 'true'
        option = data.get('option')
    except:
        keyword = ""
        option = ""
        search = False

    print(search)
    # render page with data
    return render(request, "curate.html", {
        "navbarOption": get_navbar_option(keyword, option),
        "search": search
    })


@csrf_exempt
def curate_load_file(request):
    print("this is in the curate_load_file func")
    filename = request.POST.get("filename")
    print("filename: ", filename)
    try:
        data = tsv_to_dict(filename)
        success = "true"
    except FileNotFoundError:
        data = {}
        success = "false"
    return JsonResponse({'data': data, 'success': success}, safe=False)



s = {
    'author': ('<h5>{name}</h5><p>{affiliation}, Papers: {paperCount}, Citations: {citations}</p></div>'),
         # '<div style="float: left; width: 50%; padding: 0;"><p>Papers: {paperCount}</p></div>'
         # '<div style="float: right; width: 50%; text-align: right; padding: 0;"<p>Citations: {citations}</p></div>'),
    'conference': ('<h5>{DisplayName}</h5>'
        '<div style="float: left; width: 50%; padding: 0;"><p>Papers: {PaperCount}</p></div>'
        '<div style="float: right; width: 50%; text-align: right; padding: 0;"<p>Citations: {CitationCount}</p></div>'),
    'institution': ('<h5>{DisplayName}</h5>'
        '<div style="float: left; width: 50%; padding: 0;"><p>Papers: {PaperCount}</p></div>'
        '<div style="float: right; width: 50%; text-align: right; padding: 0;"<p>Citations: {CitationCount}</p></div>'),
    'journal': ('<h5>{DisplayName}</h5>'
        '<div style="float: left; width: 50%; padding: 0;"><p>Papers: {PaperCount}</p></div>'
        '<div style="float: right; width: 50%; text-align: right; padding: 0;"<p>Citations: {CitationCount}</p></div>'),
    'paper': ('<h5>{title}</h5>'
        '<div><p>Citations: {citations}, Field: {fieldOfStudy}</p><p>Authors: {authorName}</p></div>')
}

@csrf_exempt
def search(request):
    keyword = request.POST.get("keyword")
    entityType = request.POST.get("option")
    exclude = set(string.punctuation)
    keyword = ''.join(ch for ch in keyword if ch not in exclude)
    keyword = keyword.lower()
    keyword = " ".join(keyword.split())
    id_helper_dict = {"conference": "ConferenceSeriesId", "journal": "JournalId", "institution": "AffiliationId", "paper": "eid", "author": "eid"}
    if entityType == "conference":
        data = query_conference_series(keyword)
    elif entityType == "journal":
        data = query_journal(keyword)
    elif entityType == "institution":
        data = query_affiliation(keyword)
    else:
        data = get_entities_from_search(keyword, entityType)
    for i in range(len(data)):
        entity = {'data': data[i]}
        entity['display-info'] = s[entityType].format(**entity['data'])
        entity['table-id'] = "{}_{}".format(entityType, entity['data'][id_helper_dict[entityType]])
        data[i] = entity
    return JsonResponse({'entities': data}, safe=False)


'''
s = {
    'author': ('<h5>{DisplayName}</h5><p>Papers: {PaperCount}, Citations: {CitationCount}</p></div>'),
         # '<div style="float: left; width: 50%; padding: 0;"><p>Papers: {paperCount}</p></div>'
         # '<div style="float: right; width: 50%; text-align: right; padding: 0;"<p>Citations: {citations}</p></div>'),
    'conference': ('<h5>{DisplayName}</h5>'
        '<div style="float: left; width: 50%; padding: 0;"><p>Papers: {PaperCount}</p></div>'
        '<div style="float: right; width: 50%; text-align: right; padding: 0;"<p>Citations: {CitationCount}</p></div>'),
    'institution': ('<h5>{DisplayName}</h5>'
        '<div style="float: left; width: 50%; padding: 0;"><p>Papers: {PaperCount}</p></div>'
        '<div style="float: right; width: 50%; text-align: right; padding: 0;"<p>Citations: {CitationCount}</p></div>'),
    'journal': ('<h5>{DisplayName}</h5>'
        '<div style="float: left; width: 50%; padding: 0;"><p>Papers: {PaperCount}</p></div>'
        '<div style="float: right; width: 50%; text-align: right; padding: 0;"<p>Citations: {CitationCount}</p></div>'),
    'paper': ('<h5>{PaperTitle}</h5>'
        '<div><p>Citations: {CitationCount}</p></div>')
}

idkeys = {'paper': 'PaperId', 'author': 'AuthorId', 'institution': 'AffiliationId', 'journal': 'JournalId', 'conference': 'ConferenceSeriesId'}

@csrf_exempt
def search(request):
    global idkeys
    keyword = request.POST.get("keyword")
    entity_type = request.POST.get("option")
    data = search_name(keyword, entity_type)
    idkey = idkeys[entity_type]
    for i in range(len(data)):
        # print(entity)
        entity = {'data': data[i]}
        entity['display-info'] = s[entity_type].format(**entity['data'])
        entity['table-id'] = "{}_{}".format(entity_type, entity['data'][idkey])
        data[i] = entity
        # print(entity)
    print(data[0])
    return JsonResponse({'entities': data}, safe=False)
'''

@csrf_exempt
def manualcache(request):
    cache_dictionary = (json.loads(request.POST.get('cache')))
    paper_action = request.POST.get('paperAction')
    saveNewBrowseCache(cache_dictionary)

    if paper_action == "batch":
        paper_ids = get_all_paper_ids(cache_dictionary["EntityIds"])
        addToBatch(paper_ids)
    if paper_action == "cache":
        paper_ids = get_all_paper_ids(cache_dictionary["EntityIds"])
        paper_info_mag_check_multiquery(paper_ids)
    return JsonResponse({},safe=False)


@csrf_exempt
def submit(request):

    curated_flag = False
    if request.method == "GET":
        # from url e.g.
        # /submit/?type=author_id&id=2146610949&name=stephen_m_blackburn
        # /submit/?type=browse_author_group&name=lexing_xie
        # data should be pre-processed and cached
        curated_flag = True
        data, option, config = get_url_query(request.GET)
        selected_papers = get_all_paper_ids(data["EntityIds"])
        entity_names = get_all_normalised_names(data["EntityIds"])
        keyword = ""
        flower_name     = data.get('DisplayName')

    else:
        data = json.loads(request.POST.get('data'))
         # normalisedName: <string>   # the normalised name from entity with highest paper count of selected entities
         # entities: {"normalisedName": <string>, "eid": <int>, "entity_type": <author | conference | institution | journal | paper>
        option = data.get("option")   # last searched entity type (confusing for multiple entities)
        keyword = data.get('keyword') # last searched term (doesn't really work for multiple searches)
        entity_ids = data.get('entities')
        selected_papers = get_all_paper_ids(entity_ids)
        entity_names = get_all_normalised_names(entity_ids)
        config = None
        flower_name     = data.get('flower_name')

    # Default Dates
    min_year = None
    max_year = None

    time_cur = datetime.now()

    print()
    print('Number of Papers Found: ', len(selected_papers))
    print('Time taken: ', datetime.now() - time_cur)
    print()

    time_cur = datetime.now()

    # Turn selected paper into information dictionary list
    paper_information = paper_info_mag_check_multiquery(selected_papers) # API

    # Get coauthors
    coauthors = get_coauthor_mapping(paper_information)

    print()
    print('Number of Paper Information Found: ', len(paper_information))
    print('Time taken: ', datetime.now() - time_cur)
    print()

    # Get min and maximum year
    years = [info['Year'] for info in paper_information if 'Year' in info]
    min_pub_year, max_pub_year = min(years, default=0), max(years, default=0)

    # caculate pub/cite chart data
    cont_pub_years = range(min_pub_year, max_pub_year+1)
    cite_years = set()
    for info in paper_information:
        if 'Citations' in info:
            cite_years.update({entity["Year"] for entity in info['Citations'] if "Year" in entity})

    # Add publication years as well
    cite_years.add(min_pub_year)
    cite_years.add(max_pub_year)

    min_cite_year, max_cite_year = min(cite_years, default=0), max(cite_years, default=0)
    cont_cite_years = range(min(cite_years, default=0), max(cite_years,default=0)+1)
    pub_chart = [{"year":k,"value":Counter(years)[k] if k in Counter(years) else 0} for k in cont_cite_years]
    citecounter = {k:[] for k in cont_cite_years}
    for info in paper_information:
        if 'Citations' in info:
            for entity in info['Citations']:
                citecounter[info['Year']].append(entity["Year"])

    cite_chart = [{"year":k,"value":[{"year":y,"value":Counter(v)[y]} for y in cont_cite_years]} for k,v in citecounter.items()]

    # Normalised entity names
    entity_names = list(set(entity_names))
#    normal_names = list(map(lambda x: x.lower(), entity_names))

    # TEST TOTAL TIME FOR SCORING
    time_cur = datetime.now()

    # Generate scores from paper information
    time_score = datetime.now()
    score_df = score_paper_info_list(paper_information, self=entity_names)
    print('TOTAL SCORE_DF TIME: ', datetime.now() - time_score)

    # Set up configuration of influence flowers
    flower_config = default_config
    if config:
        flower_config['self_cite'] = config[4]
        flower_config['icoauthor'] = config[5]
        flower_config['pub_lower'] = config[0]
        flower_config['pub_upper'] = config[1]
        flower_config['cit_lower'] = config[2]
        flower_config['cit_upper'] = config[3]

    # Work function
    make_flower = lambda x: gen_flower_data(score_df, x, entity_names,
            flower_name, coauthors, config=flower_config)

    # Concurrently calculate the aggregations
    # Concurrent map
    if settings.MULTIPROCESS:
        p = multiprocess.Pool(NUM_THREADS)
        flower_res = p.map(make_flower, flower_leaves)
    else: # temporary fix
        flower_res = [make_flower(v) for v in flower_leaves]
    sorted(flower_res, key=lambda x: x[0])

    # Reduce
    node_info   = dict()
    flower_info = list()
    for _, f_info, n_info in flower_res:
        flower_info.append(f_info)
        node_info.update(n_info)

    print('TOTAL FLOWER TIME: ', datetime.now() - time_cur)

    if config == None:
        config = [min_pub_year, max_pub_year, min_cite_year, max_cite_year, "false", "true"]
    else:
        config[4] = str(config[4]).lower()
        config[5] = str(config[5]).lower()

    data = {
        "author": flower_info[0],
        "conf"  : flower_info[1],
        "inst"  : flower_info[2],
        "curated": curated_flag,
        "yearSlider": {
            "title": "Publications range",
            "pubrange": [min_pub_year, max_pub_year, (max_pub_year-min_pub_year+1)],
            "citerange": [min_cite_year, max_cite_year, (max_cite_year-min_cite_year+1)],
            "pubChart": pub_chart,
            "citeChart": cite_chart,
            "selected": config
        },
        "navbarOption": get_navbar_option(keyword, option)
    }

    # Set cache
    cache = {'cache': selected_papers, 'coauthors': coauthors}

    stats = get_stats(paper_information)
    data['stats'] = stats

    # Cache from flower data
    for key, value in cache.items():
        request.session[key] = value

    for p in paper_information:
        len(p['Citations'])

    request.session['flower_name']  = flower_name
    request.session['entity_names'] = entity_names
    request.session['node_info']    = node_info
    return render(request, "flower.html", data)

@csrf_exempt
def resubmit(request):
    print(request)
    option = request.POST.get('option')
    keyword = request.POST.get('keyword')
    pre_flower_data = []
    cache        = request.session['cache']
    coauthors    = request.session['coauthors']
    flower_name  = request.session['flower_name']
    entity_names = request.session['entity_names']
    #scores = [pd.read_json(c, orient = 'index') for c in cache]

    flower_config = default_config
    flower_config['self_cite'] = request.POST.get('selfcite') == 'true'
    flower_config['icoauthor'] = request.POST.get('coauthor') == 'true'
    flower_config['pub_lower'] = int(request.POST.get('from_pub_year'))
    flower_config['pub_upper'] = int(request.POST.get('to_pub_year'))
    flower_config['cit_lower'] = int(request.POST.get('from_cit_year'))
    flower_config['cit_upper'] = int(request.POST.get('to_cit_year'))

    # Recompute flowers
    paper_information = paper_info_mag_check_multiquery(cache) # API
    score_df = score_paper_info_list(paper_information, self=entity_names)

    # Work function
    make_flower = lambda x: gen_flower_data(score_df, x, entity_names,
            flower_name, coauthors, config=flower_config)

    # Concurrently calculate the aggregations
    # Concurrent map
    if settings.MULTIPROCESS:
        p = multiprocess.Pool(NUM_THREADS)
        flower_res = p.map(make_flower, flower_leaves)
    else: # temporary fix
        flower_res = [make_flower(v) for v in flower_leaves]

    # Reduce
    node_info   = dict()
    flower_info = list()
    for _, f_info, n_info in flower_res:
        flower_info.append(f_info)
        node_info.update(n_info)

    data = {
        "author": flower_info[0],
        "conf"  : flower_info[1],
        "inst"  : flower_info[2],
        "navbarOption": get_navbar_option(keyword, option)
    }

    stats = get_stats(paper_information, flower_config['pub_lower'], flower_config['pub_upper'])
    data['stats'] = stats

    # Update the node_info cache
    request.session['node_info'] = node_info

    return JsonResponse(data, safe=False)


@csrf_exempt
def get_publication_papers(request):
    start = datetime.now()
    # request should contain the ego author ids and the node author ids separately
    print(request.POST)
    pub_year = int(request.POST.get("pub_year"))
    paper_ids = request.session['cache']
    papers = paper_info_mag_check_multiquery(paper_ids)
    papers = [paper for paper in papers if paper["Year"] == pub_year]
    for paper in papers: print(paper)
    print((datetime.now()-start).total_seconds())
    return JsonResponse({"papers": papers, "names": request.session["entity_names"]+ list(request.session["node_info"].keys())}, safe=False)

@csrf_exempt
def get_citation_papers(request):
    start = datetime.now()
    # request should contain the ego author ids and the node author ids separately
    print(request.POST)
    cite_year = int(request.POST.get("cite_year"))
    pub_year_min = int(request.POST.get("pub_year_min"))
    pub_year_max = int(request.POST.get("pub_year_max"))
    paper_ids = request.session['cache']
    papers = paper_info_mag_check_multiquery(paper_ids)
    cite_papers = [[citation for citation in paper["Citations"] if citation["Year"] == cite_year] for paper in papers if (paper["Year"] >= pub_year_min and paper["Year"] <= pub_year_max)]
    citations = sum(cite_papers,[])
    for citation in citations: print(citation)
    print((datetime.now()-start).total_seconds())
    print(request.session["node_info"].keys())
    return JsonResponse({"papers": citations, "names": request.session["entity_names"] + list(request.session["node_info"].keys())}, safe=False)


@csrf_exempt
def get_node_info(request):
    start = datetime.now()
    # request should contain the ego author ids and the node author ids separately
    print(request.POST)
    data = json.loads(request.POST.get("data_string"))
    node_name = data.get("name")

    return JsonResponse(request.session['node_info'][node_name], safe=False)