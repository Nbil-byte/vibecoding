import pandas as pd
df = pd.read_csv('data/raw/_sample_1000.csv')
texts = df['text'].fillna('').tolist()
with open('data/raw/_texts_1000.txt', 'w', encoding='utf-8') as f:
    for i, t in enumerate(texts):
        f.write(f'{i}\t{t}\n')
print('Done, wrote 1000 lines')
