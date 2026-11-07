"""Import public non-commercial map data through the source's anonymous client API.

Never reads a user's login/cookies. Tokens remain in memory. Only read endpoints
are called. Original artwork is not downloaded by this data importer.
"""
from __future__ import annotations
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
REGIONS={"MD":("mondstadt","Mondstadt"),"LY":("liyue","Liyue"),"DQ":("inazuma","Inazuma"),
         "XM":("sumeru","Sumeru"),"FD":("fontaine","Fontaine"),"NT":("natlan","Natlan"),
         "NDKL":("nod_krai","Nod-Krai"),"ZD":("snezhnaya","Snezhnaya")}
ITEM_NAMES={6:("anemoculus","Anemoculi","Oculi"),8:("common-chest","Baús comuns","Baús"),
            10:("exquisite-chest","Baús sofisticados","Baús"),16:("luxurious-chest","Baús luxuosos","Baús"),
            17:("precious-chest","Baús preciosos","Baús"),12:("time-trial","Desafios de tempo","Desafios"),
            15:("seelie","Seelies","Seelies"),31:("shrine-mondstadt","Santuários de Mondstadt","Santuários"),
            54:("wolfhook","Gancho do Lobo","Recursos"),55:("calla-lily","Copo-de-leite","Recursos"),
            56:("valberry","Valberry","Recursos"),57:("cecilia","Cecília","Recursos"),
            58:("philanemo-mushroom","Cogumelo Philanemo","Recursos"),59:("windwheel-aster","Margarida Voadora","Recursos"),
            60:("dandelion-seed","Semente de Dandelion","Recursos"),61:("small-lamp-grass","Grama do Pequeno Sino","Recursos"),
            62:("crystal-chunk","Pedaço de Cristal","Recursos"),63:("white-iron","Pedaço de Ferro Branco","Recursos"),
            64:("iron-chunk","Pedaço de Ferro","Recursos"),65:("magical-crystal","Cristal Mágico","Recursos"),
            96:("sweet-flower","Flor Doce","Recursos"),98:("mint","Menta","Recursos")}
NAME_ALIASES={
    '普通的宝箱':('common-chest','Baús comuns','Baús'),
    '精致的宝箱':('exquisite-chest','Baús sofisticados','Baús'),
    '珍贵的宝箱':('precious-chest','Baús preciosos','Baús'),
    '华丽的宝箱':('luxurious-chest','Baús luxuosos','Baús'),
    '奇馈宝箱':('remarkable-chest','Baús extraordinários','Baús'),
    '限时挑战':('time-trial','Desafios de tempo','Desafios'),
    '仙灵':('seelie','Seelies','Seelies'),
    '仙灵之庭':('seelie-court','Jardins de Seelies','Seelies'),
    '散失的风神瞳':('anemoculus','Anemoculi','Oculi'),
    '散失的岩神瞳':('geoculus','Geoculi','Oculi'),
    '散失的雷神瞳':('electroculus','Electroculi','Oculi'),
    '散失的草神瞳':('dendroculus','Dendroculi','Oculi'),
    '散失的水神瞳':('hydroculus','Hydroculi','Oculi'),
    '散失的火神瞳':('pyroculus','Pyroculi','Oculi'),
    '散失的冰神瞳':('cryoculus','Cryoculi','Oculi'),
}


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    temporary.replace(path)


class Client:
    BASE="https://cloud.yuanshen.site"
    def __init__(self):
        # These are the anonymous public-client parameters in the source frontend.
        req=urllib.request.Request(self.BASE+"/oauth/token?refresh_token=all&grant_type=client_credentials",
                                  data=b"",headers={"Authorization":"Basic "+base64.b64encode(b"client:secret").decode()})
        with urllib.request.urlopen(req,timeout=30) as response:
            self.token=json.load(response)["access_token"]

    def read(self,route,data):
        request=urllib.request.Request(self.BASE+"/api/"+route,data=json.dumps(data).encode(),
            headers={"Authorization":"Bearer "+self.token,"Content-Type":"application/json"})
        with urllib.request.urlopen(request,timeout=60) as response: result=json.load(response)
        if result.get("error"): raise RuntimeError(f"Source rejected read {route}: {result.get('message')}")
        return result["data"]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"data/community/kongying")
    parser.add_argument("--cache",type=Path,default=ROOT/"build/regional-audit/export")
    parser.add_argument("--offline",action="store_true",help="Rebuild from the audited cached export without network access")
    args=parser.parse_args()
    config_path=ROOT/'build/regional-audit/webapp.json'
    if args.offline:
        config=json.loads(config_path.read_text(encoding='utf-8'))
    else:
        with urllib.request.urlopen('https://assets.yuanshen.site/webapp.json',timeout=30) as response: config=json.load(response)
        write(config_path,config)
    client=None if args.offline else Client()
    areas=json.loads((args.cache/'areas.json').read_text(encoding='utf-8')) if args.offline else client.read("area/get/list",{"parentId":-1,"isTraverse":True})
    roots={a["id"]:REGIONS[a["code"].split(":")[1]] for a in areas
           if a["code"].startswith("C:") and a["code"].split(":")[1] in REGIONS and a.get("hiddenFlag")==0}
    leaves=[a for a in areas if a["parentId"] in roots and a.get("hiddenFlag")==0]
    write(args.cache/"areas.json",areas)
    def get(area):
        path=args.cache/f"area-{area['id']}.json"
        if path.exists(): return area,json.loads(path.read_text(encoding="utf-8"))
        if client is None: raise RuntimeError(f"Missing audited export: {path}")
        meta=client.read("item/get/list",{"areaIdList":[area["id"]],"current":0,"size":10000})
        if meta["total"]>len(meta["record"]): raise RuntimeError("Item catalog requires pagination")
        points=client.read("marker/get/list_byinfo",{"areaIdList":[area["id"]],"getBeta":0})
        data={"items":meta["record"],"markers":points}
        write(path,data);print(f"Read {area['code']}: {len(points)} points",flush=True)
        return area,data
    by_region={region:{"areas":[],"items":{},"points":{}} for region,_ in roots.values()}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for task in as_completed([pool.submit(get,a) for a in leaves]):
            area,data=task.result();region,_=roots[area["parentId"]];target=by_region[region]
            target["areas"].append(area)
            for item in data["items"]:
                if item.get("hiddenFlag")==0: target["items"][item["id"]]=item
            for point in data["markers"]:
                if point.get("hiddenFlag")!=0:continue
                entry=target["points"].setdefault(point["id"],{"point":point,"areas":set()})
                entry["areas"].add(f"ky-area-{area['id']}")
    memberships={}
    for region,target in by_region.items():
        for markerid in target['points']: memberships.setdefault(markerid,set()).add(region)
    ambiguous={markerid:sorted(regions) for markerid,regions in memberships.items() if len(regions)>1}
    write(args.output/'unclassified-points.json',dict(reason='Cross-region source associations can describe achievement accounting, not physical territory.',
          points=[dict(source_marker_id=markerid,candidate_regions=regions) for markerid,regions in sorted(ambiguous.items())]))
    stamp=datetime.now(timezone.utc).date().isoformat();territories=[];regions=[];maps={};rules={};territorial_audit={}
    # Exact legacy source IDs, not geographic proximity, determine aliases.
    aliases={}
    for file in (ROOT/"data/community/mondstadt").glob("*.json"):
        old=json.loads(file.read_text(encoding="utf-8"))
        for row in old.get("data",[]):
            for source_id in row.get("importIds",{}).get("yuanshen",[]):
                aliases[source_id]=f"teyvat.moe:mondstadt:{file.stem}:{row['id']}"
    for region,target in by_region.items():
        label=next(name for slug,name in REGIONS.values() if slug==region)
        territories.append(dict(id=region,name=label,parent_id=None,region_id=region,kind="region"))
        categories={};item_category={};metadata=target["items"]
        for itemid,meta in metadata.items():
            types=set(meta["typeIdList"])
            if 1 in types or itemid in {2713,3849}:continue
            group=("Inimigos" if 5 in types else "Recursos" if types&{3,4,6,7,8} else "Baús" if 10 in types else "Puzzles" if 11 in types else "Exploração")
            category,name,group=ITEM_NAMES.get(itemid,(f"ky-item-{itemid}",meta["name"],group))
            if "神瞳" in meta["name"]:group="Oculi"
            if "地灵龛" in meta["name"]:group="Santuários"
            if "仙灵" in meta["name"]:group="Seelies"
            if "挑战" in meta["name"]:group="Desafios"
            category,name,group=NAME_ALIASES.get(meta['name'],(category,name,group))
            item_category[itemid]=category
            if category not in categories:
                categories[category]={"name":name,"group":group,"source_name":meta["name"],"source_item_ids":[]}
            categories[category]['source_item_ids'].append(itemid)
        area_maps={};level_nodes={};leaf_layers=set()
        for area in sorted(target["areas"],key=lambda area:area['id']):
            code=area["code"]
            # Separate permanent map canvases; never fold them into surface Teyvat.
            mapid={"A:LY:CENGYAN_UG":"chasm","A:DQ:YUANXIAGONG":"enkanomiya",
                   "A:FD:ANCIENT_SEA":"sea_of_bygone_eras","A:MD:SHENDIAN":"sky_temple",
                   "A:NT:NATA4":"ancient_sacred_mountain","A:NDKL:SY":"frost_moon"}.get(code,"teyvat")
            area_maps[f"ky-area-{area['id']}"]=mapid
            maps.setdefault((region,mapid),dict(id=mapid,region_id=region,name=mapid.replace('_',' ').title(),
                             coordinate_system="kongying-world",reference_status="not_validated",source_area_codes=[]))
            maps[(region,mapid)]["source_area_codes"].append(code)
            territories.append(dict(id=f"ky-area-{area['id']}",name=area["name"],parent_id=region,
                                    region_id=region,map_id=mapid,kind="area"))
            def levels(rows,parent):
                for node in rows:
                    value=node['value']
                    identifier=f"ky-level-{region}-{value.lower().replace('@','at-')}"
                    if value not in level_nodes:
                        level_nodes[value]=identifier
                        territories.append(dict(id=identifier,name=node['label'],parent_id=parent,region_id=region,
                                                map_id=mapid,layer_id=identifier,kind='area' if node.get('children') else 'locality'))
                        if not node.get('children'): leaf_layers.add(identifier)
                        levels(node.get('children',[]),identifier)
            levels(config.get('plugins',{}).get(code,{}).get('extraConfig',{}).get('underground',{}).get('levels',[]),f"ky-area-{area['id']}")
        normalized=[]
        for markerid,entry in sorted(target["points"].items()):
            if markerid in ambiguous: continue
            point=entry["point"]
            if any(link["itemId"]==2713 for link in point["itemList"]):continue
            ids=[link["itemId"] for link in point["itemList"] if link["itemId"] in item_category]
            if not ids:continue
            tags=list(dict.fromkeys(item_category[key] for key in ids))
            # Chest quality is the icon; acquisition tags remain selectable too.
            tags.sort(key=lambda c:(c not in {"common-chest","exquisite-chest","precious-chest","luxurious-chest","remarkable-chest"},c))
            pos=[float(v) for v in point["position"].split(",")]
            underground=(point.get("extra") or {}).get("underground",{})
            areaids=sorted(entry["areas"]);mapids={area_maps[a] for a in areaids}
            mapid=next(iter(mapids)) if len(mapids)==1 else "unclassified-map"
            layer="underground-unclassified" if underground.get("is_underground") else "surface"
            known_levels=list(dict.fromkeys(level_nodes[v] for v in underground.get('region_levels',[]) if v in level_nodes))
            known_layers=[value for value in known_levels if value in leaf_layers]
            if len(known_layers)==1: layer=known_layers[0]
            refresh=point.get("refreshTime")
            renewable=any(categories[c]["group"] in {"Recursos","Inimigos"} for c in tags)
            permanent_point=any(categories[c]['group'] in {'Baús','Oculi','Seelies','Santuários','Puzzles','Desafios'} for c in tags)
            rule="unknown" if renewable or (isinstance(refresh,int) and refresh<0) else "permanent"
            if not renewable and permanent_point:
                rule='permanent'
            # Positive source durations are explicitly milliseconds in its model.
            # Negative reset codes are not guessed; remain unconfirmed.
            if isinstance(refresh,int) and refresh>0 and not permanent_point:
                rule=f"ky-unconfirmed-source-{refresh}"
                rules[rule]=dict(id=rule,kind="unknown",seconds=refresh//1000,
                    source="https://github.com/kongying-tavern/genshin-cloud-rust/blob/58f506f67aa477abbb80043c3ff1640b6e6457ba/packages/database/src/models/marker/marker.rs",
                    checked_at=stamp,note="Positive milliseconds describe source tracking metadata; no verified resource/point-specific game policy, so no automatic deadline.")
                names={categories[c]['source_name'] for c in tags}
                if '圣遗物调查点' in names and refresh in {43200000,86400000}:
                    rule=f'ky-artifact-investigation-{refresh//3600000}h'
                    rules[rule]=dict(id=rule,kind='elapsed',seconds=refresh//1000,
                        source='https://keqingmains.com/misc/artifacts/',checked_at=stamp,
                        note='KQM verifies 12h/24h per investigation spot; explicit source per-point milliseconds select the branch. Other values remain unconfirmed.')
                elif '钓点' in names:
                    rule='ky-fishing-conditional'
                    rules[rule]=dict(id=rule,kind='conditional',seconds=259200,
                        source='https://gamewith.net/genshin-impact/article/show/29632',checked_at=stamp,
                        note='Three-day fishing guidance does not prove full depletion of separate day/night stocks. No automatic deadline for a generic collection toggle.')
                if refresh==165600000:
                    rules[rule]['note']='Source has 46h, while local specialty guidance says 48h (https://www.icy-veins.com/genshin-impact/farming-guides). Contradictory: no deadline.'
            identifier=aliases.get(point.get("markerStamp")) if region=="mondstadt" else None
            normalized.append(dict(id=identifier or f"kongying:{region}:marker:{markerid}",name=point.get("markerTitle") or categories[tags[0]]["name"],
                category=tags[0],category_ids=tags,x=pos[0],y=pos[1],region_id=region,map_id=mapid,layer_id=layer,
                area_id=known_levels[0] if known_levels else areaids[0] if len(areaids)==1 else "unclassified",
                area_ids=list(dict.fromkeys(known_levels+(areaids if len(areaids)==1 else []))),layer_ids=known_layers,rule_id=rule,
                source_area_ids=areaids,
                source_marker_id=markerid,source_stamp=point.get('markerStamp'),source_refresh_value=refresh))
        # Plugin trees repeat caves across area menus. Menu placement is not
        # ownership: use unanimous explicit marker-area links, or a shared root.
        nodes={n['id']:n for n in territories if n['region_id']==region}
        children={identifier:[] for identifier in nodes}
        for node in nodes.values():
            if node['parent_id'] in children: children[node['parent_id']].append(node['id'])
        owners={identifier:set() for identifier in nodes}
        for point in normalized:
            memberships=set(point['source_area_ids']) if len(point['source_area_ids'])==1 else {None}
            for identifier in point['area_ids']:
                if identifier.startswith('ky-level-'): owners[identifier].update(memberships)
        def subtree_owners(identifier):
            result=set(owners[identifier])
            for child in children[identifier]: result.update(subtree_owners(child))
            return result
        for node in nodes.values():
            original=node['parent_id']
            if not original or not original.startswith('ky-area-'): continue
            explicit=subtree_owners(node['id'])
            if not explicit: continue
            owner=next(iter(explicit)) if len(explicit)==1 else None
            parent=owner if owner in nodes and nodes[owner]['map_id']==node['map_id'] else region
            if parent!=original:
                territorial_audit[node['id']]=dict(source_parent=original,parent=parent,
                    explicit_point_areas=sorted(v for v in explicit if v),
                    reason='unanimous_marker_area' if parent!=region else 'shared_or_unconfirmed_area')
                node['parent_id']=parent
        out=args.output/region;write(out/"markers.json",{"items":normalized})
        digest=hashlib.sha256((out/"markers.json").read_bytes()).hexdigest()
        write(out/"SOURCE.json",dict(project="Kongying Tavern",region_id=region,license="CC-BY-NC-SA-4.0",version=stamp,
              source="https://yuanshen.site/docs/en/disclaimer",coordinate_system="kongying-world",categories=categories,
              files=[dict(file="markers.json",format="normalized-v1",sha256=digest)]))
        regions.append(dict(id=region,name=label,catalog=f"kongying/{region}",item_count=len(normalized),coordinate_system="kongying-world"))
        print(f"Imported {label}: {len(normalized)} unique markers",flush=True)
    write(args.output/"inventory.json",dict(version=1,snapshot=stamp,regions=regions,maps=list(maps.values()),territories=territories,
          coverage_complete=False,territorial_audit=territorial_audit,unclassified_region_count=len(ambiguous),notes=["Repeated plugin menu trees do not establish geographic ownership; explicit point associations determine parents or a shared root.","Cross-region achievement associations are quarantined, never assigned by proximity.","Localities and exact underground floors require additional verified classification.",
          "Names without a verified Portuguese translation retain the source name.","Reference presence is not live validation."]))
    write(args.output/"respawn-rules.json",{"rules":list(rules.values())})
    codes={code for mapmeta in maps.values() for code in mapmeta['source_area_codes']}
    bases={config['tiles'][code].get('extend') for code in codes}
    write(args.output/'source-map-config.json',dict(source='https://assets.yuanshen.site/webapp.json',snapshot=stamp,
          license='CC-BY-NC-SA-4.0',tiles={key:value for key,value in config['tiles'].items() if key in codes|bases},
          plugins={key:value for key,value in config.get('plugins',{}).items() if key in codes}))


if __name__=="__main__": main()
