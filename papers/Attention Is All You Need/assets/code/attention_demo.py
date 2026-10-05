import math
import json

X = [[1, 0, 1, 0], [0, 1, 0, 2], [1, 1, 2, 1]]

def attention(x, head=0, causal=False):
    # 教学投影：第一头的 Q/K 取前两维、V 取后两维；第二头交换。
    qk_cols, v_cols = ((0, 1), (2, 3)) if head == 0 else ((2, 3), (0, 1))
    q = [[row[j] for j in qk_cols] for row in x]
    k = q
    v = [[row[j] for j in v_cols] for row in x]
    weights, output = [], []
    for i, query in enumerate(q):
        scores = [sum(a*b for a,b in zip(query,key))/math.sqrt(2) for key in k]
        scores = [s if not causal or j <= i else -math.inf for j,s in enumerate(scores)]
        exps = [math.exp(s-max(scores)) for s in scores]
        alpha = [e/sum(exps) for e in exps]
        weights.append(alpha)
        output.append([sum(alpha[j]*v[j][d] for j in range(len(x))) for d in range(2)])
    return weights, output

for head in (0, 1):
    weights, z = attention(X, head=head)
    print(json.dumps({"head":head+1,"first_weights":[round(a,6) for a in weights[0]],
                      "first_output":[round(a,6) for a in z[0]]}))
print("causal first output:", attention(X, causal=True)[1][0])
