# WikiTableSet

WikiTableSet is a largest publicly available image-based table recognition dataset in three languages built from Wikipedia.
WikiTableSet contains nearly 4 million English table images, 590K Japanese table images, 640k French table images with corresponding HTML representation, and cell bounding boxes.
We build a Wikipedia table extractor [WTabHTML](https://github.com/phucty/wtabhtml) and use this to extract tables (in HTML code format) from the 2022-03-01 dump of Wikipedia. In this study, we select Wikipedia tables from three representative languages, i.e., English, Japanese, and French; however, the dataset could be extended to around 300 languages with 17M tables using our table extractor. 
Second, we normalize the HTML tables following the PubTabNet format (separating table headers and table data, removing CSS and style tags). Finally, we use Chrome and Selenium to render table images from table HTML codes. 
This dataset provides a standard benchmark for studying table recognition algorithms in different languages or even multilingual table recognition algorithms.

## Getting data

* The Japanese part (WikiTableSet_JA) of the dataset can be downloaded in [OneDrive]().
* The 750K English table images (WikiTableSet-EN750K) from the English part of WikiTableSet in [OneDrive]().
* The whole table images in the English part and the French part will be released soon.

Directory structure of the dataset is :

```shell
.
├── train
│   ├── 1.png
│   ├── 3.png
│   ├── 4.png
│   └── ...
├── val
│   ├── 106.png
│   ├── 107.png
│   ├── 117.png
│   └── ...
├── test
│   ├── 384.png
│   ├── 385.png
│   ├── 531.png
│   └── ...
├── WikiTableNet_1.0_ja_table_train.jsonl
├── WikiTableNet_1.0_ja_table_val.jsonl
└── WikiTableNet_1.0_ja_table_test.jsonl
```

## Annotation structure

The annotation is in the jsonl (jsonlines) format, where each line contains the annotations on a given sample in the following format:
The structure of the annotation jsonl file is:

```
{
   'filename': str,
   'split': str,
   'imgid': int,
   'html': {
     'structure': {'tokens': [str]},
     'cell': [
       {
         'tokens': [str],
         'bbox': [x0, y0, x1, y1]  # only non-empty cells have this attribute
       }
     ]
   }
}
```

## Cite us

```
@article{icpram23,
  title={Rethinking Image-Based Table Recognition Using Weakly Supervised Methods},
  author={Nam Ly. and Atsuhiro Takasu. and Phuc Nguyen. and Hideaki Takeda.},
  booktitle={Proceedings of the 12th International Conference on Pattern Recognition Applications and Methods - ICPRAM,},
  year={2023},
  pages={872-880},
  doi={10.5220/0011682600003411},
}
```

## Contact
Nam Ly (namly@nii.ac.jp)

## First: 
parse wiki jsonl file into table images and table json by wiki_table_parser.py.
<br>
python3 wiki_table_parser.py -s 1 -e 1000

## Second: 
merge json file of each table into jsonl file.
<br>
python3 merge_json_files.py
