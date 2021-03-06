import networkx as nx
import logging
import edgesense.utils as eu
from datetime import datetime

def set_isolated(nodes_list, mdg):
    ts = int(datetime.now().strftime("%s"))
    dsg = extract_dpsg(mdg, ts, True)
    usg = dsg.to_undirected()
    isolated_nodes = set(nx.isolates(usg))
    for node in nodes_list:
        if node['id'] in isolated_nodes:
            node['isolated'] = True
        
def extract_dpsg(mdg, ts, team=True):
    dg=nx.DiGraph()
    # add all the nodes present at the time ts
    for node in mdg.nodes_iter():
        if mdg.node[node]['created_ts'] <= ts and (team or not mdg.node[node]['team']):
            dg.add_node(node, mdg.node[node])
    
    for node in dg.nodes_iter():
        for neighbour in mdg[node].keys():
            count = sum(1 for e in mdg[node][neighbour].values() if e['ts'] <= ts and (team or not e['team']))
            effort = sum(e['effort'] for e in mdg[node][neighbour].values() if e['ts'] <= ts and (team or not e['team']))
            team_edge = sum(1 for e in mdg[node][neighbour].values() if e['ts'] <= ts and e['team'])>0
            # an edge should be added here only if either ends are included
            if count > 0 and (team or not team_edge) and dg.has_node(neighbour):
               dg.add_edge(node, neighbour, {'source': node, 'target': neighbour, 'effort': effort, 'count': count, 'team': team_edge}) 
    
    return dg

def build_network(network):
    MDG=nx.MultiDiGraph()

    for node in network['nodes']:
        MDG.add_node(node['id'], node)

    for edge in network['edges']:
        MDG.add_edge(edge['source'], edge['target'], attr_dict=edge)
    
    set_isolated(network['nodes'], MDG)
    
    return MDG

def extract_edges(nodes_map, comments_map):
    # build the list of edges
    edges_list = []
    # a comment is 'valid' if it has a recipient and an author
    valid_comments = [e for e in comments_map.values() if e.get('recipient_id', None) and e.get('author_id', None)]
    logging.info("%(v)i valid comments on %(t)i total" % {'v':len(valid_comments), 't':len(comments_map.values())})
    
    # build the whole network to use for metrics
    for comment in valid_comments:
        link = {
            'id': "{0}_{1}_{2}".format(comment['author_id'],comment['recipient_id'],comment['created_ts']),
            'source': comment['author_id'],
            'target': comment['recipient_id'],
            'ts': comment['created_ts'],
            'effort': comment['length'],
            'team': comment['team']
        }
        if nodes_map.has_key(comment['author_id']):
            nodes_map[comment['author_id']]['active'] = True
        else:
            logging.info("error: node %(n)s was linked but not found in the nodes_map" % {'n':comment['author_id']})  
    
        if nodes_map.has_key(comment['recipient_id']):
            nodes_map[comment['recipient_id']]['active'] = True
        else:
            logging.info("error: node %(n)s was linked but not found in the nodes_map" % {'n':comment['recipient_id']})  
        edges_list.append(link)


    return sorted(edges_list, key=eu.sort_by('ts'))

def extract_inactive_nodes(nodes_map):
    # filter out nodes that have not participated to the full:conversations
    inactive_nodes = []
    for node_id in nodes_map.keys():
        if not nodes_map[node_id]['active']:
            inactive_nodes.append(nodes_map.pop(node_id, None))

    return inactive_nodes
