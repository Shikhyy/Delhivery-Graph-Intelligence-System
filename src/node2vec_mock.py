class Node2Vec:
    def __init__(self, G, dimensions=32, *args, **kwargs):
        self.nodes = list(G.nodes())
        self.dimensions = dimensions
    def fit(self, *args, **kwargs):
        class Model:
            pass
        model = Model()
        model.wv = {str(n): [0.0]*self.dimensions for n in self.nodes}
        return model
