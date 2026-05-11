import math
from typing import List


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000  # metros
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def detectar_clusters(leaks: list, radio_m: int) -> List[List[int]]:
    """
    leaks: lista de dicts con keys {leak_id, actual_x (lon), actual_y (lat)}
    Retorna lista de grupos (listas de leak_ids).
    """
    n = len(leaks)
    if n == 0:
        return []

    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(i + 1, n):
            lat1 = leaks[i].get("actual_y") or 0
            lon1 = leaks[i].get("actual_x") or 0
            lat2 = leaks[j].get("actual_y") or 0
            lon2 = leaks[j].get("actual_x") or 0
            if lat1 == 0 or lat2 == 0:
                continue
            dist = haversine_m(lat1, lon1, lat2, lon2)
            if dist <= radio_m:
                union(i, j)

    # Agrupar
    groups: dict = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(leaks[i]["leak_id"])

    return [g for g in groups.values() if len(g) >= 2]
