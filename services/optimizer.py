import math
from typing import List

def calculate_distance(p1, p2):
    return math.sqrt((p1['lat'] - p2['lat'])**2 + (p1['lng'] - p2['lng'])**2)

def generate_optimized_batch(orders: List[dict]):
    """
    Algorithme du voisin le plus proche pour le groupage Dakarois.
    """
    if not orders: return []
    optimized_path = []
    current_pos = {"lat": orders[0]['latitude'], "lng": orders[0]['longitude']}
    
    remaining = orders[:]
    while remaining:
        nearest = min(remaining, key=lambda x: calculate_distance(current_pos, {"lat": x['latitude'], "lng": x['longitude']}))
        optimized_path.append(nearest)
        current_pos = {"lat": nearest['latitude'], "lng": nearest['longitude']}
        remaining.remove(nearest)
        
    return optimized_path