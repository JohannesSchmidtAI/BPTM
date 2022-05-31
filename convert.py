import xml.etree.ElementTree as ET
import pandas as pd
import xmltodict
import json
import numpy as np
import warnings
import sys
 
 

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=np.VisibleDeprecationWarning)


def print_to_stdout(*a):
 
    print(*a, file = sys.stdout)


def flatten(l):
    l_flatt = []
    for x in l:
        if isinstance(x,list):
            for sub_x in x:
                l_flatt.append(sub_x)
        else:
            l_flatt.append(x)
    return l_flatt

def convert_ids(obj,mapping):
    if isinstance(obj,list):
        new_obj = []
        for x in obj:
            if x in mapping.keys():
                new_obj.append(mapping[x])
            else:
                new_obj.append(x)
    else:
        if obj in mapping.keys(): 
            new_obj = [mapping[obj]]
        else:
            new_obj = obj


    return new_obj


def convert(bpmn):    


    with open(bpmn, 'r') as myfile:
        obj = xmltodict.parse(myfile.read())


    tasks_types = ['sendTask','receiveTask','userTask','serviceTask','parallelGateway','exclusiveGateway']

    df = pd.DataFrame()
    for tt in tasks_types:
        for elm in obj['definitions']['process'][tt]:
            df = df.append((pd.Series({'Name':elm['@name'],'Incoming':elm['incoming'],'Outgoing':elm['outgoing'],'Type':tt})),ignore_index=True)

    all_incoming_outgoing = np.unique(flatten(df.Incoming.values) + flatten(df.Outgoing.values))
    inc_out_mapping =  {Id:i for i,Id in enumerate (all_incoming_outgoing)}



    for idx in df.index:
        data = df.loc[idx]


        incoming = convert_ids(data['Incoming'],inc_out_mapping)
        outgoing = convert_ids(data['Outgoing'],inc_out_mapping)

        df.loc[idx]['Incoming'] = incoming
        df.loc[idx]['Outgoing'] = outgoing


    idxs_out = []
    #Loop over outgoing rows
    for j in df.index:
        data_j = df.loc[j]

        outgoing = data_j['Outgoing']

        idx_out = []
        #Loop over incoming rows
        for k in df.index:

            data_k = df.loc[k]

            incoming = data_k['Incoming']
            #Loop over all items of one specific outgoing row/column 
            for t_out in outgoing:
                if t_out in incoming:
                    idx_out.append(k)



        idxs_out.append(idx_out)



    idxs_in = []
    #Loop over outgoing rows
    for j in df.index:
        data_j = df.loc[j]

        incoming = data_j['Incoming']

        idx_in = []
        #Loop over incoming rows
        for k in df.index:

            data_k = df.loc[k]

            outgoing = data_k['Outgoing']
            #Loop over all items of one specific outgoing row/column 
            for t_out in incoming:
                if t_out in outgoing:
                    idx_in.append(k)



        idxs_in.append(idx_in)    


    df['Ids_in'] = idxs_in
    df['Ids_out'] = idxs_out
    df['index'] = df.index

    df.drop(columns=['Incoming', 'Outgoing'],inplace=True)




    transactions = {}
    for idx in df.index:
            out = "out "
            inx = " in "


            previous_ones = df.loc[idx]['Ids_in']
            me = df.loc[idx]
            next_ones = df.loc[idx]['Ids_out']
            mask_excl_opening = (me['Type'] == 'exclusiveGateway' and len(me['Ids_out']) > 1)
            mask_excl_closing = (me['Type'] == 'exclusiveGateway' and len(me['Ids_in']) > 1)
            name = me['Name']

            #Start place
            if(len(previous_ones)==0):
                previous_ones = [-1]
            #End place
            elif(len(next_ones)==0):
                next_ones = [-2]

            ###############  Tx-out    ########################
            for outgoing in next_ones:

                #Self - opening exclusive gateway
                if(mask_excl_opening):

                    transactions[str(idx)+str(outgoing)] = {'In': [], 'Out': [], 'Name':[]}
                    transactions[str(idx)+str(outgoing)]['Out'].append(str(idx) + str(outgoing))
                    transactions[str(idx)+str(outgoing)]['In'].append(str(previous_ones[0])+str(idx))

                elif(not(str(idx) in transactions) and not(mask_excl_closing)):

                    transactions[str(idx)] = {'In': [], 'Out': [], 'Name':[]}
                    transactions[str(idx)]['Out'].append(str(idx)+str(outgoing))

                    if(name!=''):
                        transactions[str(idx)]['Name'] = [name]

                elif (not(mask_excl_closing)):

                    transactions[str(idx)]['Out'].append(str(idx)+str(outgoing))
                    if(name!=''):
                        transactions[str(idx)]['Name'] = [name]

            ###############  Tx-in    ########################
            for incoming in previous_ones:

                #Self - closing exclusive gateway
                if(mask_excl_closing):

                    transactions[str(incoming)+str(next_ones[0])] = {'In': [], 'Out': [], 'Name':[]}
                    transactions[str(incoming)+str(next_ones[0])]['In'].append(str(incoming)+str(idx))
                    transactions[str(incoming)+str(next_ones[0])]['Out'].append(str(idx) + str(next_ones[0]))                


                elif(not(str(idx) in transactions) and not(mask_excl_opening)):

                    transactions[str(idx)] = {'In': [], 'Out': [], 'Name':[]}
                    transactions[str(idx)]['In'].append(str(incoming)+str(idx))                

                elif (not(mask_excl_opening)):

                    transactions[str(idx)]['In'].append(str(incoming)+str(idx))


    final_out = ""

    values = []
    mapping = {}

    for i in transactions.keys():
        for k in ('In','Out'):
            values.append(transactions[i][k])
    values = np.unique(flatten(values))
    mapping = {e:str(i) for i,e in enumerate(values)}

    for i in values:

        place = f"place P{mapping[i]}" + ";\n"

        final_out += place

    for i,idx in enumerate(transactions):
            out_2 = " out "
            inx = " in "
            t_name = ""

            out_raw = ["\"P"+str(mapping[x])+"\"" for x in transactions[idx]['Out']]
            in_raw = ["\"P"+str(mapping[x])+"\"" for x in transactions[idx]['In']]

            if (transactions[idx]['Name']):
                t_name = f"~\"{str(transactions[idx]['Name'])[2:-2]}\""

            out_next = str(out_raw)[1:-1].replace("'","")
            in_next = str(in_raw)[1:-1].replace("'","")


            out_2 = out_2 + out_next
            inx = inx + in_next


            out_2 = f"trans \"T{i}\""+ t_name +  inx + out_2 + ";\n"

            final_out += out_2
    
    print_to_stdout(final_out)
    #print(final_out)
    
    return final_out


if __name__== "__main__":
    convert(sys.argv[1])
    