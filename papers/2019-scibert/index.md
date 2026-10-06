# SciBert: предобученная языковая модель для научных текстов

> **Неофициальный перевод.** Оригинал: Iz Beltagy, Kyle Lo, Arman Cohan. «SciBERT: A Pretrained Language Model for Scientific Text». EMNLP-IJCNLP, 2019. DOI: [10.18653/v1/D19-1371](https://doi.org/10.18653/v1/D19-1371). Лицензия: CC BY 4.0.

## Аннотация

Получение крупномасштабных аннотированных данных для задач обработки естественного языка в научной сфере представляет собой сложную и дорогостоящую задачу. Для преодоления нехватки качественных, крупномасштабных размеченных научных данных мы выпускаем модель SciBert – предобученную языковую модель, основанную на Bert [Devlin et al. (2019)]. Данная модель использует процесс предобучения без участия разметки на обширном мультидоменном корпусе научных публикаций, что способствует повышению эффективности решения последующих задач обработки естественного языка в научной области. Мы провели оценку модели на ряде задач, включая тегирование последовательностей, классификацию предложений и синтаксический анализ, используя наборы данных из различных научных областей. Полученные результаты показывают статистически значимое улучшение показателей по сравнению с моделью Bert; на нескольких задачах SciBert достигла новых рекордных результатов. Код и предобученные модели доступны по адресу [https://github.com/allenai/scibert/](https://github.com/allenai/scibert/).

## Введение

За последние десятилетия объем научных публикаций стремительно возрос, вследствие чего обработка естественного языка стала незаменимым инструментом для масштабного извлечения знаний и машинного чтения подобных документов. В последнее время развитие обработки естественного языка обусловлено применением глубоких нейронных моделей; однако для их обучения зачастую требуется большое количество размеченных данных. В общих областях получение таких данных в больших объемах часто возможно посредством краудсорсинга; однако в научных областях сбор аннотированных данных представляет собой сложную и дорогостоящую задачу из-за необходимости привлечения специалистов для качественной аннотации.

Как показали исследования с использованием Elmo [Peters et al. (2018)], GPT [Radford et al. (2018)] и Bert [Devlin et al. (2019)], безнадзорная предобучение языковых моделей на больших корпусах данных существенно повышает их эффективность при решении множества задач в области обработки естественного языка. Эти модели выдают контекстуализированные эмбеддинги для каждого токена, которые затем можно использовать в небольших нейронных архитектурах, специфичных для конкретной задачи. Применение подходов безнадзорного предобучения приобрело особую актуальность в ситуациях, когда получение аннотированных данных для задачи затруднено, как, например, в научной обработке естественного языка. Однако, несмотря на то, что как Bert, так и Elmo предоставляют предобученные модели, они по-прежнему обучались на корпусах данных из общедоступных сфер — новостных статей и Википедии.

В данной работе мы делаем следующие вклады:

(*i*) Мы представляем SciBert — новый ресурс, способствующий повышению эффективности решения различных задач обработки естественного языка в научной сфере. SciBert представляет собой предобученную языковую модель, основанную на архитектуре Bert, однако обученную на обширном корпусе научных текстов.

*ii* Мы провели обширные эксперименты с целью изучения эффективности дообучения по сравнению с использованием архитектур, специально разработанных для конкретных задач при неизменных эмбеддингах, а также влияния наличия лексики, соответствующей научной области.

*iii* Мы тестируем модель SciBert на ряде задач в научной сфере и добиваемся новых рекордных (SOTA) результатов по многим из этих задач.

## Методы

## Экспериментальная установка

### Задачи

Мы проводим эксперименты по следующим ключевым задачам обработки естественного языка:

PICO, подобно задаче распознавания именованных сущностей, представляет собой задачу разметки последовательностей: модель выделяет фрагменты текста, описывающие участников, вмешательства, сравнения и результаты в клиническом исследовании [Kim et al. (2011)]. Задача REL является частным случаем классификации текста: модель определяет тип отношения, существующего между двумя сущностями; эти сущности в предложении выделяются с помощью специальных токенов.

### Наборы данных

Для краткости здесь описываются лишь новые наборы данных; более старые наборы описаны в ссылках, приведённых в таблице 1. В наборе данных EBM-NLP [Nye et al. (2018)] размечаются фрагменты текста формата PICO в аннотациях к клиническим исследованиям. В наборе SciERC [Luan et al. (2018)] размечаются сущности и отношения в аннотациях по информатике. В наборах ACL-ARC [Jurgens et al. (2018)] и SciCite [Cohan et al. (2019)] предпринимается попытка присвоить предложениям из научных статей, цитирующих другие работы, метки намерения (например, «Сравнение», «Расширение» и т. д.). Набор данных Paper Field создан на основе графа Microsoft Academic Graph [Sinha et al. (2015)]33 [https://academic.microsoft.com/](https://academic.microsoft.com/); он сопоставляет названия статей с одной из 7 областей науки. Для каждой из этих областей (география, политология, экономика, бизнес, социология, медицина и психология) имеется примерно 12 тысяч обучающих примеров.

### Предобученные варианты модели BERT

### Дообучение модели BERT

Мы в основном придерживаемся той же архитектуры, методов оптимизации и выбора гиперпараметров, что и в [Devlin et al. (2019)]. При классификации текстов (то есть задачах типа CLS и REL) в линейный классификатор подается итоговый вектор модели Bert, соответствующий токену `[CLS]`. При разметке последовательностей (то есть задачах типа NER и PICO) в линейный классификатор с выходом в виде распределения softmax подаются итоговые векторы модели Bert для каждого токена. Небольшое отличие заключается в использовании дополнительного условного случайного поля; это упростило оценку результатов, поскольку гарантировало корректную структуру выделенных сущностей. Для задачи DEP мы применяем модель из [Dozat and Manning (2017)], в которой используются эмбеддинги тегов зависимостей и дуг размером 100, а также биаффинное матричное внимание к векторам модели Bert вместо каскадных слоев BiLSTM.

Во всех экспериментах мы применяем **dropout** с коэффициентом 0.1 и оптимизируем функцию потерь в виде кросс-энтропии с использованием алгоритма **Adam** [Kingma and Ba (2015)]. Для дообучения модели проводится от 2 до 5 эпох при размере пакета 32 и различных значениях скорости обучения: 5e-6, 1e-5, 2e-5 или 5e-5. При этом используется график изменения скорости обучения в форме наклонного треугольника [Howard and Ruder (2018)], эквивалентный линейному разогреву с последующим линейным затуханием [Devlin et al. (2019)]. Для каждого набора данных и варианта модели **Bert** мы выбираем оптимальное значение скорости обучения и количества эпох на основе результатов на валидационной выборке, после чего приводим соответствующие результаты на тестовой выборке.

Мы установили, что наилучшими параметрами для большинства наборов данных и моделей являются 2 или 4 эпохи обучения при скорости обучения, равной 2e-5. Хотя оптимальные гиперпараметры зависят от конкретной задачи, они зачастую совпадают для всех вариантов модели Bert.

### Замороженные эмбеддинги Bert

Мы также исследуем возможность использования Bert в качестве предобученных контекстуализированных словных эмбеддингов, подобных ELMo [Peters et al. (2018)], путем обучения простых моделей, специфичных для конкретных задач, на основе замороженных эмбеддингов Bert.

Для задачи классификации текстов мы подаём входные векторы, полученные от модели Bert, в двухслойную архитектуру BiLSTM, состоящую из двух направлений обработки; размер каждого слоя равен 200. Затем на объединённые векторы первого и последнего слоёв BiLSTM применяется многослойный перцептрон (с размером скрытого слоя 200). В задаче разметки последовательностей используются те же слои BiLSTM, а для обеспечения корректности предсказаний применяется условное случайное поле. Для задачи синтаксического анализа мы используем полную модель из [Dozat and Manning (2017)]; размерность векторов зависимостей и дуг равна 100, а конфигурация слоёв BiLSTM аналогична другим задачам. Мы не обнаружили, чтобы изменение глубины или размера слоёв BiLSTM существенно влияло на результаты [Reimers and Gurevych (2017)].

Мы оптимизируем функцию потерь кросс-энтропии с помощью алгоритма Адам, при этом веса модели Берт остаются неизменными, а коэффициент дропаута установлен на уровне 0.5. Обучение проводится с использованием механизма ранней остановки на выборке для валидации (с порогом в 10 эпох); размер пакета составляет 32, а скорость обучения — 0.001.

Мы не проводили тщательного поиска гиперпараметров; однако, хотя оптимальные гиперпараметры, вероятно, зависят от конкретной задачи, небольшие эксперименты показали, что данные настройки довольно хорошо работают для большинства задач и различных вариантов модели Bert.

Проводились тесты всех вариантов модели Bert на всех задачах и наборах данных. **Жирным шрифтом** выделены результаты, соответствующие SOTA (если разница между несколькими результатами не превышает 95% доверительного интервала по методу бутстрепа, все они выделяются жирным шрифтом). В соответствии с предыдущими исследованиями приводятся значения макро-F1 для задачи NER (на уровне спанов), макро-F1 для задач REL и CLS (на уровне предложений), а также макро-F1 для задачи PICO (на уровне токенов); для задачи ChemProt отдельно указывается значение микро-F1. Для задачи DEP приводятся значения оценок прикрепления с учетом меток (LAS) и без учета меток (UAS) (знаки препинания не учитываются); эти значения получены для одной и той же модели с гиперпараметрами, оптимизированными под LAS. Все результаты представляют собой средние значения по нескольким запускам с различными начальными значениями случайных чисел.

## Результаты

В таблице 1 приводятся итоги экспериментов. Мы отмечаем, что модель SciBert превосходит модель Bert-Base в решении научных задач (+2.11 балла по метрике F1 при дообучении и +2.43 балла без него)88. В дальнейшем в данной работе все приводимые результаты усредняются по наборам данных с исключением показателей UAS для задачи DEP, поскольку для нее уже учитываются показатели LAS. Кроме того, с использованием модели SciBert нам удалось достичь новых рекордных результатов во многих из этих задач.

### Биомедицинская область

Мы отмечаем, что SciBert превосходит Bert-Base в биомедицинских задачах (+1.92 F1 при дообучении и +3.59 F1 без него). Кроме того, SciBert позволяет достичь новых рекордных результатов в задачах BC5CDR и ChemProt [Lee et al. (2019)], а также EBM-NLP [Nye et al. (2018)].

Модель SciBert показывает несколько худшие результаты по сравнению с SOTA на трех наборах данных. SOTA-модель для задачи JNLPBA представляет собой **ансамбль** (ensemble) из сетей типа BiLSTM-CRF, обученный на множестве наборов данных для распознавания именованных сущностей, а не только на JNLPBA [Yoon et al. (2018)]. SOTA-модель для задачи распознавания заболеваний NCBI — это BioBert [Lee et al. (2019)]; данная модель представляет собой версию Bert-Base, дообученную на 18 миллиардах токенов из биомедицинских статей. Наилучший результат для набора данных GENIA зафиксирован в работе [Nguyen and Verspoor (2019)]; в ней используется модель из [Dozat and Manning (2017)] с учетом признаков частей речи (POS), которыми мы не пользуемся.

В таблице 2 мы сравнивают результаты работы модели SciBert с опубликованными результатами модели BioBert на подмножестве наборов данных, включенных в [Lee et al. (2019)]. Примечательно, что SciBert превосходит BioBert по показателям на наборах данных BC5CDR и ChemProt; при этом на наборе данных JNLPBA его результаты сопоставимы с результатами BioBert, несмотря на то, что SciBert обучался на значительно меньшем корпусе биомедицинских текстов.

Сравнение модели SciBert с ранее опубликованными результатами модели BioBert на биомедицинских наборах данных.

### Область компьютерных наук

Мы отмечаем, что SciBert превосходит модель Bert-Base в задачах в области информатики (при финитюнинге показатель F1 увеличивается на 3.55, а без финитюнинга — на 1.13). Кроме того, SciBert демонстрирует новые рекордные результаты на наборе данных ACL-ARC [Cohan et al. (2019)], а также в задаче распознавания именованных сущностей из набора SciERC [Luan et al. (2018)]. Что касается распознавания отношений в SciERC, наши результаты нельзя сопоставить с результатами из [Luan et al. (2018)]: мы проводим классификацию отношений при наличии заранее известных сущностей, тогда как в указанной работе выполняется совместное извлечение сущностей и отношений.

### Множество доменов

Мы отмечаем, что SciBert превосходит Bert-Base в задачах, охватывающих несколько доменов (при дообучении показатель F1 увеличивается на 0.49, а без дообучения — на 0.93). Кроме того, SciBert превосходит текущий уровень достижений в области обработки научных текстов на датасете SciCite [Cohan et al. (2019)]. Для датасета Paper Field ранее не публиковались результаты, соответствующие текущему уровню достижений.

## Обсуждение

### Влияние дообучения

Мы наблюдаем улучшение результатов при дообучении модели Bert по сравнению с использованием архитектур, специально разработанных для конкретных задач на основе «замороженных» эмбеддингов (в среднем повышение показателя F1 на 3.25 при использовании SciBert и на 3.58 при использовании Bert-Base). Для каждой научной области наибольший эффект от дообучения наблюдается в задачах в области информатики (повышение F1 на 5.59 при использовании SciBert и на 3.17 при использовании Bert-Base) и биомедицинских задачах (повышение F1 на 2.94 при использовании SciBert и на 4.61 при использовании Bert-Base); наименьший эффект отмечается в задачах, затрагивающих несколько областей (повышение F1 лишь на 0.7 при использовании SciBert и на 1.14 при использовании Bert-Base). На всех наборах данных, кроме BC5CDR и SciCite, модель Bert-Base с дообучением показывает лучшие результаты (или сопоставимые результаты) по сравнению с моделью, использующей «замороженные» эмбеддинги SciBert.

### Влияние SciVocab

Мы оцениваем важность наличия специализированной научной лексики в данной области, повторяя эксперименты по дообучению модели SciBert с использованием словаря BaseVocab. Мы обнаружили, что оптимальные гиперпараметры для модели SciBert-BaseVocab зачастую совпадают с гиперпараметрами модели SciBert-SciVocab.

В среднем по всем наборам данных использование SciVocab позволяет повысить показатель F1 на +0.60. В рамках каждой научной области наблюдается прирост показателя F1 на +0.76 для биомедицинских задач, на +0.61 — для задач в области информатики и на +0.11 — для задач мультидоменного характера.

Учитывая разрозненность лексиконов (раздел 2) и значительность улучшения показателей по сравнению с моделью Bert-Base (раздел Результаты), мы предполагаем, что, несмотря на полезность использования лексикона, специфичного для конкретной области, модель SciBert получает наибольшую выгоду от предварительного обучения на научном корпусе.

## Связанные исследования

В последнее время в области адаптации BERT к конкретной предметной области появилось несколько моделей, в том числе BioBert [Lee et al. (2019)], ClinicalBert [Alsentzer et al. (2019)] и [Huang et al. (2019)]. BioBert обучается на аннотациях из PubMed и полных текстах статей из базы PMC; ClinicalBert — на клинических текстах из базы данных MIMIC-III [Johnson et al. (2016)]. В отличие от них, SciBert обучается на полных текстах 1.14 миллиона статей по биомедицине и информатике из корпуса Semantic Scholar [Ammar et al. (2018)]. Кроме того, SciBert использует специально разработанный для данной области словарь (SciVocab), тогда как вышеупомянутые модели применяют стандартный словарь Bert (BaseVocab).

## Заключение и перспективы дальнейших исследований

Мы выпустили SciBert — предобученную языковую модель для научных текстов, созданную на основе Bert. Мы протестировали SciBert на ряде задач и наборах данных из научной сферы. SciBert значительно превзошел модель Bert-Base и продемонстрировал новые рекордные результаты по ряду этих задач; при этом он также превосходит некоторые опубликованные результаты модели BioBert [Lee et al. (2019)] в области биомедицинских задач.

В рамках дальнейших исследований мы выпустим версию SciBert, аналогичную Bert-Large, а также проведем эксперименты с различными соотношениями статей из разных областей. Поскольку обучение подобных языковых моделей требует значительных затрат, нашей целью является создание единого ресурса, полезного для использования в нескольких областях.

## Благодарности

Мы благодарим анонимных рецензентов за их комментарии и предложения. Также благодарим Валида Аммара, Ноха Смита, Йоава Голдберга, Дэниела Кинга, Дага Дауни и Дэна Уэлда за полезные обсуждения и отзывы. Все эксперименты проводились на платформе [beaker.org](https://beaker.org); частичная поддержка осуществлялась за счёт кредитов от Google Cloud.

## Список литературы

Alsentzer et al. (2019) Alsentzer et al. (2019) Emily Alsentzer, John R. Murphy, Willie Boag, Wei-Hung Weng, Di Jin, Tristan Naumann, and Matthew B. A. McDermott. 2019. Publicly available clinical bert embeddings. In ClinicalNLP workshop at NAACL.
Ammar et al. (2018) Ammar et al. (2018) Waleed Ammar, Dirk Groeneveld, Chandra Bhagavatula, Iz Beltagy, Miles Crawford, Doug Downey, Jason Dunkelberger, Ahmed Elgohary, Sergey Feldman, Vu Ha, Rodney Kinney, Sebastian Kohlmeier, Kyle Lo, Tyler Murray, Hsu-Han Ooi, Matthew Peters, Joanna Power, Sam Skjonsberg, Lucy Lu Wang, Chris Wilhelm, Zheng Yuan, Madeleine van Zuylen, and Oren Etzioni. 2018. Construction of the literature graph in semantic scholar. In NAACL.
Cohan et al. (2019) Cohan et al. (2019) Arman Cohan, Waleed Ammar, Madeleine van Zuylen, and Field Cady. 2019. Structural scaffolds for citation intent classification in scientific publications. In NAACL-HLT, pages 3586–3596, Minneapolis, Minnesota. Association for Computational Linguistics.
Collier and Kim (2004) Collier and Kim (2004) Nigel Collier and Jin-Dong Kim. 2004. Introduction to the bio-entity recognition task at jnlpba. In NLPBA/BioNLP.
Dettmers (2019) Dettmers (2019) Tim Dettmers. 2019. TPUs vs GPUs for Transformers (BERT). http://timdettmers.com/2018/10/17/tpus-vs-gpus-for-transformers-bert/. Accessed: 2019-02-22.
Devlin et al. (2019) Devlin et al. (2019) Jacob Devlin, Ming-Wei Chang, Kenton Lee, and Kristina Toutanova. 2019. BERT: Pre-training of deep bidirectional transformers for language understanding. In NAACL-HLT.
Dogan et al. (2014) Dogan et al. (2014) Rezarta Islamaj Dogan, Robert Leaman, and Zhiyong Lu. 2014. NCBI disease corpus: A resource for disease name recognition and concept normalization. Journal of biomedical informatics, 47:1–10.
Dozat and Manning (2017) Dozat and Manning (2017) Timothy Dozat and Christopher D. Manning. 2017. Deep biaffine attention for neural dependency parsing. ICLR.
Gardner et al. (2017) Gardner et al. (2017) Matt Gardner, Joel Grus, Mark Neumann, Oyvind Tafjord, Pradeep Dasigi, Nelson F. Liu, Matthew Peters, Michael Schmitz, and Luke S. Zettlemoyer. 2017. Allennlp: A deep semantic natural language processing platform. In arXiv:1803.07640.
Howard and Ruder (2018) Howard and Ruder (2018) Jeremy Howard and Sebastian Ruder. 2018. Universal language model fine-tuning for text classification. In ACL.
Huang et al. (2019) Huang et al. (2019) Kexin Huang, Jaan Altosaar, and Rajesh Ranganath. 2019. Clinicalbert: Modeling clinical notes and predicting hospital readmission. arXiv:1904.05342.
Johnson et al. (2016) Johnson et al. (2016) Alistair E. W. Johnson, Tom J. Pollard aand Lu Shen, Liwei H. Lehman, Mengling Feng, Mohammad Ghassemi, Benjamin Moody, Peter Szolovits, Leo Anthony Celi, , and Roger G. Mark. 2016. Mimic-iii, a freely accessible critical care database. In Scientific Data, 3:160035.
Jurgens et al. (2018) Jurgens et al. (2018) David Jurgens, Srijan Kumar, Raine Hoover, Daniel A. McFarland, and Daniel Jurafsky. 2018. Measuring the evolution of a scientific field through citation frames. TACL, 06:391–406.
Kim et al. (2003) Kim et al. (2003) Jin-Dong Kim, Tomoko Ohta, Yuka Tateisi, and Jun’ichi Tsujii. 2003. GENIA corpus - a semantically annotated corpus for bio-textmining. Bioinformatics, 19:i180–i182.
Kim et al. (2011) Kim et al. (2011) Su Kim, David Martínez, Lawrence Cavedon, and Lars Yencken. 2011. Automatic classification of sentences to support evidence based medicine. In BMC Bioinformatics.
Kingma and Ba (2015) Kingma and Ba (2015) Diederik P. Kingma and Jimmy Ba. 2015. Adam: A method for stochastic optimization. ICLR.
Kringelum et al. (2016) Kringelum et al. (2016) Jens Kringelum, Sonny Kim Kjærulff, Søren Brunak, Ole Lund, Tudor I. Oprea, and Olivier Taboureau. 2016. ChemProt-3.0: a global chemical biology diseases mapping. In Database.
Lee et al. (2019) Lee et al. (2019) Jinhyuk Lee, Wonjin Yoon, Sungdong Kim, Donghyeon Kim, Sunkyu Kim, Chan Ho So, and Jaewoo Kang. 2019. BioBERT: a pre-trained biomedical language representation model for biomedical text mining. In arXiv:1901.08746.
Li et al. (2016) Li et al. (2016) Jiao Li, Yueping Sun, Robin J. Johnson, Daniela Sciaky, Chih-Hsuan Wei, Robert Leaman, Allan Peter Davis, Carolyn J. Mattingly, Thomas C. Wiegers, and Zhiyong Lu. 2016. BioCreative V CDR task corpus: a resource for chemical disease relation extraction. Database : the journal of biological databases and curation.
Luan et al. (2018) Luan et al. (2018) Yi Luan, Luheng He, Mari Ostendorf, and Hannaneh Hajishirzi. 2018. Multi-task identification of entities, relations, and coreference for scientific knowledge graph construction. In EMNLP.
Neumann et al. (2019) Neumann et al. (2019) Mark Neumann, Daniel King, Iz Beltagy, and Waleed Ammar. 2019. ScispaCy: Fast and robust models for biomedical natural language processing. In arXiv:1902.07669.
Nguyen and Verspoor (2019) Nguyen and Verspoor (2019) Dat Quoc Nguyen and Karin M. Verspoor. 2019. From pos tagging to dependency parsing for biomedical event extraction. BMC Bioinformatics, 20:1–13.
Nye et al. (2018) Nye et al. (2018) Benjamin Nye, Junyi Jessy Li, Roma Patel, Yinfei Yang, Iain James Marshall, Ani Nenkova, and Byron C. Wallace. 2018. A corpus with multi-level annotations of patients, interventions and outcomes to support language processing for medical literature. In ACL.
Peters et al. (2018) Peters et al. (2018) Matthew E. Peters, Mark Neumann, Mohit Iyyer, Matt Gardner, Christopher Clark, Kenton Lee, and Luke S. Zettlemoyer. 2018. Deep contextualized word representations. In NAACL-HLT.
Radford et al. (2018) Radford et al. (2018) Alec Radford, Karthik Narasimhan, Tim Salimans, and Ilya Sutskever. 2018. Improving language understanding by generative pre-training.
Reimers and Gurevych (2017) Reimers and Gurevych (2017) Nils Reimers and Iryna Gurevych. 2017. Optimal hyperparameters for deep lstm-networks for sequence labeling tasks. In EMNLP.
Sinha et al. (2015) Sinha et al. (2015) Arnab Sinha, Zhihong Shen, Yang Song, Hao Ma, Darrin Eide, Bo-June Paul Hsu, and Kuansan Wang. 2015. An overview of microsoft academic service (MAS) and applications. In WWW.
Vaswani et al. (2017) Vaswani et al. (2017) Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, and Illia Polosukhin. 2017. Attention is all you need. In NIPS.
Wu et al. (2016) Wu et al. (2016) Yonghui Wu, Mike Schuster, Zhifeng Chen, Quoc V. Le, Mohammad Norouzi, Wolfgang Macherey, Maxim Krikun, Yuan Cao, Qin Gao, Jeff Klingner, Apurva Shah, Melvin Johnson, Xiaobing Liu, Lukasz Kaiser, Stephan Gouws, Yoshikiyo Kato, Taku Kudo, Hideto Kazawa, Keith Stevens, George Kurian, Nishant Patil, Wei Wang, Cliff Young, Jason Smith, Jason Riesa, Alex Rudnick, Oriol Vinyals, Gregory S. Corrado, Macduff Hughes, and Jeffrey Dean. 2016. Google’s neural machine translation system: Bridging the gap between human and machine translation. abs/1609.08144.
Yoon et al. (2018) Yoon et al. (2018) Wonjin Yoon, Chan Ho So, Jinhyuk Lee, and Jaewoo Kang. 2018. CollaboNet: collaboration of deep neural networks for biomedical named entity recognition. In DTMBio workshop at CIKM.
