#from convert import convert
import pandas as pd
import numpy as np
from operator import add
import seaborn as sns
import matplotlib.pyplot as plt
import sys
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=np.VisibleDeprecationWarning)

m_count = int(0)

def print_to_stdout(*a):
 
    print(*a, file = sys.stdout)
    
    
def find_between(s,first,last):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

def find_trans (df,trans,n_row):

    global m_count
    
    for t in trans:
        count = 0
        l = []
        for in_p in trans[t]['in']:
            if count == 0:
                mask = df.columns[1:-1] == in_p
                count +=1
            else:
                mask2 = df.columns[1:-1] == in_p
                mask = list( map(add, mask, mask2))
        
        l = [df.iloc[:,1:-1].loc[n_row, mask].values.tolist()]

        if not(0 in (item for sublist in l for item in sublist)):
            
            if(len(df.loc[n_row,'Transition'])>0):
                 
                    df.loc[n_row,'Transition'] = str(df.loc[n_row,'Transition']) + ","+ "T" + str(t)+ "->M" + str(m_count)
                    m_count +=1
            else:
   
                    df.loc[n_row,'Transition'] = "T" + str(t) + "->M" + str(m_count)
                    m_count+=1

    return df


def fire_trans(df,trans,input_row):
    
    if(len(df)-1<input_row):
        return df
    
    next_up = df.loc[input_row,'Transition'].replace('T','').split(',')
    
    # If no more transitions possible (e.g. last final token reached)
    if(len(next_up[0])==0):
        return df
    
    new_next_up = []
    
    int_count = 0
    
    global m_count

    for n in next_up:
        
        transition = n.split('->')[0]
        position = int(n.split('->')[1][1:])

                
        #Check how output row would look like to check if this combination already exists
        in_places = trans[int(transition)]['in']
        out_places = trans[int(transition)]['out']

        check_df = df.iloc[input_row:input_row+1,1:-1].copy()

        for i in in_places:
            check_df.loc[input_row:,i] = check_df.loc[input_row:,i] -1

        for o in out_places:
            check_df.loc[input_row:,o] = check_df.loc[input_row:,o] +1
            
        check_array = np.array(check_df)[0]
            
        ball = np.count_nonzero(df.iloc[:,1:-1].values == check_array,axis=1)
        
        #If output combination already exists refer to this one instead of creating new row entry
        if len(df.columns)-2 in ball:
            
            newe = np.argwhere(ball==len(df.columns)-2).flatten()[0]
            newe = df.loc[newe,'M']
            
            if int_count == 0:
                new_next_up.append("T" + str(transition) + "->M" + str(newe))
                int_count+=1
            else:
                new_next_up.append("," + "T" + str(transition) + "->M" + str(newe))
            
        else:
            
            df = df.append(df.iloc[input_row,:-1],ignore_index=True)

            output_row = df.index[-1] 

            df.loc[output_row,'M'] = position
            df.loc[output_row, 'Transition'] = ""


            for i in in_places:
                df.loc[output_row:,i] = df.loc[output_row:,i] -1

            for o in out_places:
                df.loc[output_row:,o] = df.loc[output_row:,o] +1
            
            if int_count == 0:            
                new_next_up.append("T" + str(transition) + "->M" + str(position))
                int_count+=1
            else:
                new_next_up.append("," + "T" + str(transition) + "->M" + str(position))
            
    string_next = "".join([str(item) for item in new_next_up])
    df.loc[input_row, 'Transition'] = string_next

    return df

################################################################################

def reachability(tpn_raw):

    global m_count    
    
    with open(tpn_raw) as f:
        tpn = f.read()
    
    
    str1 = tpn.replace(";","").replace("'","").split("\n")[0:-1]
    
    out_trans = []
    for i,t in enumerate(str1):
        if("trans" in t[0:5]):
            
            if ("~" in t):
                if (i<10):
                    out_trans.append(find_between(t,"trans \"","\"") + " ... " + find_between(t,"~\"","\"").replace("\\n","").replace("\\",""))
                else:
                    out_trans.append(find_between(t,"trans \"","\"") + " ..." + find_between(t,"~\"","\"").replace("\\n","").replace("\\",""))
            else:
                if (i<10):
                    out_trans.append(find_between(t,"trans \"","\"") + " ... [Silent Gateway Transition]")
                else:
                    out_trans.append(find_between(t,"trans \"","\"") + " ...[Silent Gateway Transition]")
            
    final_out_trans = ""
    
    for i in out_trans:
        final_out_trans += i + "\n"
        

    places = []
    for p in str1:
        if ("place" in p[0:5]):
            places.append(p.replace("place ",""))

    trans = {}
    count = 0
    for t in str1:
        if ("trans" in t[0:5]):
            trans[count] = {'in':[],'out':[]}
            trans[count]['in'].append(t[t.index("\" in \"") + len("in ")+2:t.index(" out")].replace("\"",""))
            trans[count]['out'].append(t[t.index("\" out \"") + len("out ")+2:].replace("\"",""))
            count+= 1

    for t in trans:
        if(',' in trans[t]['in'][0]):
            trans[t]['in'] = trans[t]['in'][0].split(', ')
        if(',' in trans[t]['out'][0]):
            trans[t]['out'] = trans[t]['out'][0].split(', ')        



    #####################################################################################

    search = {}
    start_place = ""
    end_place = ""

    for p in places:
        search[p] = {'in':[],'out':[]}


    for t in trans:
        for p in trans[t]['in']:
            search[p]['in'].append('1')
        for p_out in trans[t]['out']:
            search[p_out]['out'].append('1')

    for pl in search:
        if len(search[pl]['out']) == 0:
            start_place = pl
        if len(search[pl]['in']) == 0:
            end_place = pl

    df = pd.DataFrame()

    df['M'] =np.NaN
    for p in places:
        df[p] = np.NaN
    df['Transition'] = ""

    df = df.append(pd.Series(m_count, index=df.columns[:1]), ignore_index=True)

    m_count+=1

    df.loc[: , start_place] = 1
    df.loc[: , 'Transition'] = ""

    df.iloc[:,:len(df.columns)-1] = df.iloc[:,:len(df.columns)-1].fillna(0).astype(int)

    last_searched = 0

    for i in range(0,500):

        for x in range(last_searched,df.index[-1]+1): 
            df = find_trans(df,trans,x)

        last_searched = df.index[-1]+1

        if(len(df)-1<i):
            break
        df = fire_trans(df,trans,i)

    for x in range(last_searched,df.index[-1]+1): 
        df = find_trans(df,trans,x)
    
    final_output = final_out_trans + "\n"
    
    final_output += df.to_string(index=False)
    
    print_to_stdout(final_output)

if __name__== "__main__":
    reachability(sys.argv[1])
        