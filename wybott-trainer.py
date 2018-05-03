import markovify
#import nltk
#import string

sentences = []
# Make this file with:
# python wybott-corpus.py > quotes.wyatt
# jq '.[]._source.text' quotes.wyatt -r > quotes.wyatt.raw
# TODO: Pull this all together in one python script
with open('quotes.wyatt.raw') as f:
    for line in f:
        if "has joined the channel" in line:
            continue

        sentences.append(line)
        #tokens = nltk.casual_tokenize(line)
        # Strip mentions:
        # for token in tokens:
        #     if (token.startswith('@') or
        #         (token.startswith('<') and token.endswith('>')) or
        #         (token in string.punctuation)):
        #         continue
        #     token_list.append(token)

# tokens_flat = ' '.join(token_list)
# print(tokens_flat)


text_model = markovify.Text(' '.join(sentences), state_size=2)
with open('wybott.model.json', 'w') as f:
    f.write(text_model.to_json())

