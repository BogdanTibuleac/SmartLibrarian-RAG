def normalize_distances(distances: list[float]) -> list[float]:
    min_dist = min(distances)
    max_dist = max(distances)
    if max_dist == min_dist:
        return [0.0 for _ in distances]
    return [(d - min_dist) / (max_dist - min_dist) for d in distances]


def approximate_cosine_distance(l2_distance: float) -> float:
    return max(0.0, min(1.0, (l2_distance ** 2) / 2))
