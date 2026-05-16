import mysql.connector
import argparse
import sys
import graphviz
from mysql.connector.abstracts import MySQLConnectionAbstract

def _esc(s):
    if s is None:
        return ""
    return str(s).replace('\\', '\\\\').replace('"', '\\"')

def build_graph(
        conn: MySQLConnectionAbstract | mysql.connector.pooling.PooledMySQLConnection
        ) -> graphviz.Digraph:
    cur = conn.cursor(dictionary=True)

    def fetch(table):
        try:
            cur.execute(f"SELECT * FROM {table}")
            return cur.fetchall()
        except Exception:
            return []

    windows = fetch('window_node')
    widgets = fetch('widget')
    edges = fetch('trans_edge')
    menu_items = fetch('menu_item')
    sub_menus = fetch('sub_menu')
    dep_widgets = fetch('dep_widget')

    g = graphviz.Digraph('UTG')
    g.attr(rankdir='LR')
    g.attr('node', fontname='Helvetica')

    # Windows
    for w in windows:
        wid = w.get('id')
        label = w.get('window_label') or w.get('window_name') or f'window_{wid}'
        g.node(f'w{wid}', label=_esc(label), shape='box')

    # Widgets
    for u in widgets:
        uid = u.get('id')
        label = u.get('widget_text') or u.get('widget_id_name') or u.get('listener_name') or f'widget_{uid}'
        g.node(f'u{uid}', label=_esc(label), shape='ellipse')
        act = u.get('act_id')
        if act is not None:
            g.edge(f'w{act}', f'u{uid}', label='contains', arrowhead='none')

    # Dep widgets (additional relation info)
    for d in dep_widgets:
        did = d.get('id')
        name = d.get('widget_id_name') or d.get('widget_type') or f'dep_{did}'
        g.node(f'd{did}', label=_esc(name), shape='diamond')

    # Menu items and submenus as nodes attached to windows
    for m in menu_items:
        mid = m.get('id')
        label = m.get('text') or m.get('widget_type') or f'menu_{mid}'
        g.node(f'm{mid}', label=_esc(label), shape='oval')
        menu_id = m.get('menu_id')
        if menu_id:
            g.edge(f'w{menu_id}', f'm{mid}', label='menu')

    for s in sub_menus:
        sid = s.get('id')
        label = s.get('text') or s.get('widget_type') or f'sub_{sid}'
        g.node(f's{sid}', label=_esc(label), shape='oval')
        menu_id = s.get('menu_id')
        if menu_id:
            g.edge(f'w{menu_id}', f's{sid}', label='submenu')

    # Transition edges between windows
    for e in edges:
        s = e.get('swindow_id')
        t = e.get('twindow_id')
        if s is None or t is None:
            continue
        label = e.get('edge_label') or e.get('trans_type') or ''
        widget_id = e.get('widget_id')
        lbl = _esc(label)
        if widget_id:
            g.edge(f'w{s}', f'w{t}', label=f'{lbl} / widget:{widget_id}')
        else:
            g.edge(f'w{s}', f'w{t}', label=lbl)

    cur.close()
    return g

def _parse_and_run():
    p = argparse.ArgumentParser(description='Export android DB as DOT graph')
    p.add_argument('--host', default='localhost')
    p.add_argument('--user', default='root')
    p.add_argument('--password', default='1234')
    p.add_argument('--database', default='android')
    args = p.parse_args()
    try:
        conn = mysql.connector.connect(host=args.host, user=args.user, password=args.password, database=args.database)
        graph = build_graph(conn)
        graph.render('utg_graph', format='png', cleanup=True)
    except mysql.connector.Error as ex:
        print('Error connecting to database:', ex, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    _parse_and_run()