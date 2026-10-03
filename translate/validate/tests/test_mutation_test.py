from translate.validate import mutation_test as mt


def test_mutation_recall_is_100():
    recall = mt.mutation_recall()
    assert set(recall) == {name for name, _ in mt.MUTATIONS}
    missed = [name for name, caught in recall.items() if not caught]
    assert missed == [], f"verify missed mutations: {missed}"
    assert all(recall.values())
