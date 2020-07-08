import glob
import os
import datetime
import re
import en_core_web_sm
import random
import requests
import json
import pandas as pd
from spellchecker import SpellChecker
from spacy.lang.pt.stop_words import STOP_WORDS
from sklearn.feature_extraction.text import CountVectorizer
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from io import StringIO
from api_keys_config import words_api_key

def pdf_to_text(pdfname):
    rsrcmgr = PDFResourceManager()
    sio = StringIO()
    laparams = LAParams()
    device = TextConverter(rsrcmgr, sio, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    # Extract text
    with open(pdfname, 'rb') as f:
        for page in PDFPage.get_pages(f):
            interpreter.process_page(page)
        f.close()

    # Get text from StringIO
    text = sio.getvalue()

    # Cleanup
    device.close()
    sio.close()
    return text

# given a string, it summarizes the text then filters out the top X number of sentences
# num_sentences = int, the number of sentences our summary should contain
def summarizer(text, num_sentences = 4):
    nlp = en_core_web_sm.load()
    doc = nlp(text)
    corpus = [sent.text.lower() for sent in doc.sents ]
    cv = CountVectorizer(stop_words=list(STOP_WORDS))   
    cv_fit=cv.fit_transform(corpus)
    word_list = cv.get_feature_names()
    count_list = cv_fit.toarray().sum(axis=0)    
    word_frequency = dict(zip(word_list,count_list))
    
    val=sorted(word_frequency.values())
    
    # Check words with higher frequencies
    higher_word_frequencies = [word for word,freq in word_frequency.items() if freq in val[-3:]]
    print("\nWords with higher frequencies: ", higher_word_frequencies)
    
    # gets relative frequencies of words
    higher_frequency = val[-1]
    for word in word_frequency.keys():  
        word_frequency[word] = (word_frequency[word]/higher_frequency)
    
    # SENTENCE RANKING: the rank of sentences is based on the word frequencies
    sentence_rank={}
    for sent in doc.sents:
        for word in sent :       
            if word.text.lower() in word_frequency.keys():            
                if sent in sentence_rank.keys():
                    sentence_rank[sent]+=word_frequency[word.text.lower()]
                else:
                    sentence_rank[sent]=word_frequency[word.text.lower()]
            else:
                continue
    
    top_sentences=(sorted(sentence_rank.values())[::-1])
    top_sent=top_sentences[:num_sentences]# number of sentances we want
    
    # Mount summary
    summary=[]
    for sent,strength in sentence_rank.items():  
        if strength in top_sent:
            summary.append(sent)
    summarized = ""
    for i in summary:
        summarized = summarized + str(i) +' '
    return summarized

# get the parts of speech for each sentence in the given text
# return a pandas dataframe with the parts of speech for each sentence (row 0 = first sentence)
def get_pos(text):
    sentences = text.split('.')
    nlp = en_core_web_sm.load()
    df = pd.DataFrame() # store parts of speech by sentence in summary
    verbs = []
    nouns = []
    adverbs = []
    adjectives = []
    for i in range(len(sentences)):
        # picking an arbitrary number to filter how long a sentnce should be. If its less than 5 characters, odds are it isnt a sentence
        if len(sentences[i])<=5: 
            continue
        doc = nlp(sentences[i])
        spacy_dataframe = pd.DataFrame()
        for token in doc:
            if token.lemma_ == "-PRON-":
                    lemma = token.text
            else:
                lemma = token.lemma_
            row = {
                "Word": token.text,
                "Lemma": lemma,
                "PoS": token.pos_,
                "Stop Word": token.is_stop
            }
            spacy_dataframe = spacy_dataframe.append(row, ignore_index = True)
        verbs.append([spacy_dataframe["Lemma"][spacy_dataframe["PoS"] == "VERB"].values,spacy_dataframe["Lemma"][spacy_dataframe["PoS"] == "VERB"].index])
        nouns.append([spacy_dataframe["Lemma"][spacy_dataframe["PoS"] == "NOUN"].values,spacy_dataframe["Lemma"][spacy_dataframe["PoS"] == "NOUN"].index])
        adverbs.append([spacy_dataframe["Lemma"][spacy_dataframe["PoS"] == "ADV"].values,spacy_dataframe["Lemma"][spacy_dataframe["PoS"] == "ADV"].index])
        adjectives.append([spacy_dataframe["Lemma"][spacy_dataframe["PoS"] == "ADJ"].values,spacy_dataframe["Lemma"][spacy_dataframe["PoS"] == "ADJ"].index])
    df['verbs'] = verbs
    df['nouns'] = nouns
    df['adverbs'] = adverbs
    df['adj'] = adjectives
    
    return df

# formats a text file to match a lab report (intro (our summary), data section, list of questions, and conclusion)
# returns the file_name so we can use that file to upload to google drive
def to_file(title,numQuestions,summarized):
    # code to get the lab report number and correctly name the file
    file_name = "Brian_Blakely_lab_report.txt"
    if os.path.isfile(file_name):
        lab_count = 1
        while True:
            lab_count += 1
            new_file_name = file_name.split(".txt")[0] + str(lab_count) + ".txt"
            if os.path.isfile(new_file_name):
                continue
            else:
                file_name = new_file_name
                break
    with open(file_name,'w+') as final_file:
        final_file.write('Brian Blakely\n')
        final_file.write('PHYS 2020, Lab '+str(lab_count)+'\n')
        final_file.write(str(datetime.datetime.today().date())+'\n')
        final_file.write(title+'\n\n')
        final_file.write('Introduction\n')
        final_file.write(summarized+'\n\n')
        final_file.write('Data and Analysis\n')
        final_file.write('<insert calculations here>\n\n')
        final_file.write('Questions\n')
        for i in range(numQuestions):
            final_file.write('Question '+str(i+1)+':\n\n')
        final_file.write('Conclusion\n')
        final_file.write('In this lab I ___ (which proved/I learned/which taught) ___ . This property can be found in the real world all over the place. An example of that is ___ .')
        final_file.close()
    return file_name

# uploads the text file to my google drive as a google doc
def to_google_doc(file_name):
    g_login = GoogleAuth()
    g_login.LocalWebserverAuth()
    drive = GoogleDrive(g_login)
    
    with open(file_name,"r") as f:
        fn = os.path.basename(f.name)
        file_drive = drive.CreateFile({'title': fn,'mimeType':'text/plain' })  
        file_drive.SetContentString(f.read()) 
        file_drive.Upload()
        print ("The file: " + fn + " has been uploaded")
    
# takes a text block and then changes one verb in a sentence with a synonym for each sentence
# this is kind of bad though since the API used to get the synonym doesnt let you specify the part of speech
def paraphrase(text):
    df = get_pos(s)

    # for consistency, we should probably just replace verbs with synonyms
    headers = {
        'x-rapidapi-host': "wordsapiv1.p.rapidapi.com",
        'x-rapidapi-key': words_api_key
        }
    sentences_temp = s.split('.')
    sentences =[]
    for i in range(len(sentences_temp)):
        if len(sentences_temp[i]) < 5:
            continue
        sentences.append(sentences_temp[i])
    
    replacement = ""
    for i in range(len(sentences)):
        ran = random.randint(0,len(df.iloc[i]['verbs'][0])-1)
        replaced = df.iloc[i]['verbs'][0][ran]
        url = 'https://wordsapiv1.p.rapidapi.com/words/'+replaced+'/synonyms'
        r= requests.request("GET", url, headers=headers)
        syn = random.choice(list(pd.read_json(json.dumps(r.json()))['synonyms']))
        replacement += sentences[i].replace(replaced,syn)+'.'
    return replacement

def main():
    path = r"F:\Pdf\random school\lab"
    os.chdir(path)
    for file in glob.glob("*.pdf"):
        print(file[:-4])
    title = file[:-4]
    path= path + '\\'+file
    
    raw_text=pdf_to_text(path)
    
    # first lets grab only the introduction
    t = re.search(r'I: Introduction \n.*?II: Procedure', raw_text, re.DOTALL).group()
    t = re.sub("\(.*?\)",'',t)
    t = t.replace('\n',' ').replace('I: Introduction ','').replace('II: Procedure','').replace(' .','.') # fix minor issues
    t= re.sub('\s+',' ',t) # replace multiple spaces
    # Change from 2nd person to first person, so the summary will look like I wrote it and didn't copy it
    forms = {'you':'I','''you're''':'I am','your':'the','You':'I','''You're''':'I am','Your':'The'}
    for word, replacer in forms.items():
        t = t.replace(word,replacer)
    # check if text block starts with a space or ends with a space
    if t[0] == ' ':
        t = t[1:]
    if t[-1] == ' ':
        t = t[:-1]
        
    summarized = summarizer(t)
    # summary_para = paraphrase(summarized) # not really that good
    numQuestions = len(re.findall(r'\b(\w*Question\w*) .\b:',raw_text)) # number of questions to answer
    file_name = to_file(title,numQuestions,summarized)
    to_google_doc(file_name)
    
if __name__ == '__main__':
    main()
    

