import os, sys
from django.shortcuts import render
from datetime import datetime
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_DIR = os.path.join(os.path.dirname(BASE_DIR), 'python')
sys.path.insert(0, PYTHON_DIR)

from flower_bloomer import getFlower
from mkAff import getAuthor, getJournal, getConf

entity_of_interest = {'author': getAuthor, 'conf': getConf}

AuthorList = []
ConferenceList = []
JournalList = []
InstitutionList = []
def loadAuthorList():
    global AuthorList
    path = os.path.join(BASE_DIR, "webapp/cache/AuthorList.txt")
    if len(AuthorList) == 0:
        with open(path, "r") as f:
            AuthorList = [name.strip() for name in f]
    AuthorList = list(set(AuthorList))
    return AuthorList

def loadConferenceList():
    global ConferenceList
    path = os.path.join(BASE_DIR, "webapp/cache/ConferenceList.txt")
    if len(ConferenceList) == 0:
        with open(path, "r") as f:
            ConferenceList = [conf.strip() for conf in f]
        ConferenceList = list(set(ConferenceList))
    return ConferenceList

def loadJournalList():
    global JournalList
    path = os.path.join(BASE_DIR, "webapp/cache/JournalList.txt")
    if len(JournalList) == 0:
        with open(path, "r") as f:
            JournalList = [journ.strip() for journ in f]
        JournaList = list(set(JournalList))
    return JournalList

def loadInstitutionList():
    global InstitutionList
    path = os.path.join(BASE_DIR, "webapp/cache/InstitutionList.txt")
    if len(InstitutionList) == 0:
        with open(path, "r") as f:
            InstitutionList = [journ.strip() for journ in f]
        Institutionist = list(set(InstitutionList))
    return InstitutionList

selfcite = False

def main(request):
    optionlist = [  # option list
        {"id":"author", "name":"Author", "list": loadAuthorList()},
        {"id":"conf", "name":"Conference", "list": loadConferenceList()},
        {"id":"journal", "name":"Journal", "list": loadJournalList()},
        {"id":"inst", "name":"Institution", "list": loadInstitutionList()}
    ]
    global keyword, option, selfcite
    keyword = ""
    option = optionlist[0] # default selection
    inflflower = None
    entities = []

    # get user input from main.html page
    if request.method == "GET":
        print(request.GET)
        if "self-cite" in request.GET:
            selfcite = True
            print("SELF_CITE")
        if "search" in request.GET:
            global id_pid_dict
            keyword = request.GET.get("keyword")
            option = [x for x in optionlist if x.get('id', '') == request.GET.get("option")][0]
            if keyword != "":
                print("{}\t{}\t{}".format(datetime.now(), __file__ , entity_of_interest[option['id']].__name__))
                entities, id_pid_dict =  entity_of_interest[option['id']](keyword) #(authors_testing, dict()) # getAuthor(keyword)

            # path to the influence flowers
            inflin = os.path.join(BASE_DIR, "output/flower1.png")
            inflby = os.path.join(BASE_DIR, "output/flower2.png")
            if option.get('id') == 'conf':
                print("{}\t{}\t{}".format(datetime.now(), __file__ , getFlower.__name__))
                inflflower = getFlower(id_2_paper_id=id_pid_dict, name=keyword, ent_type='conf', self_cite=selfcite)
            else:
                inflflower = []#[inflin, inflby]
        if "submit" in request.GET:
            selected_ids = request.GET.getlist("authorlist")
            id_2_paper_id = dict()
            for aid in selected_ids:
                id_2_paper_id[aid] = id_pid_dict[aid]
            print("{}\t{}\t{}".format(datetime.now(), __file__ , getFlower.__name__))
            print("selfcite :" + str(selfcite))
            inflflower = getFlower(id_2_paper_id=id_2_paper_id, name=keyword, ent_type='author', self_cite=selfcite)

    # render page with data
    return render(request, "main.html", {
        "optionlist": optionlist,
        "selectedKeyword": keyword,
        "selectedOption": option,
        "inflflower": inflflower,
        "authors": entities,
        "selfcite": selfcite
    })
