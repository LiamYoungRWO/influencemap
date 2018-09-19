# Influencemap Project @ ANU

Influence in the academic communities has been an area of interest for researchers. This can be seen in the popularity of applications like google scholar and the various metrics created for ranking papers, authors, conferences, etc.

We aim to provide a visualization tool which allows users to easily search and visualize the flow of academic influence. Our visualization maps influence in the form of an influence flower. We calculate influence as a function of the number of citations between two entities (look below for information on our definition of influence).

<p align="center">
  <img src="https://github.com/csmetrics/influencemap/blob/master/assets/img/example_flower_1.png"/>
</p>

The node in the center of the flower denotes the ego entity, the entitiy in which we are looking at influence with respect to. The leaf nodes are the most influential entities with respect to the ego. (We define the ego as a collection of papers. If it is an author, it is the collection of papers that the author has authored)

Each of the edges of the graph signifies the flow of influence to and from the ego node, the strenth of this relation is reflected in the thickness of the edge. The red edges denotes the influence the ego has towards the outer entities (an outer entity citing a paper by the ego). The blue edges denotes the influence the outer entities have towards the ego (the ego cites a paper by one of the outer entities).

<p align="center">
  <img src="https://github.com/csmetrics/influencemap/blob/master/assets/img/influence_flow.svg"/>
</p>

The hue of the outer nodes signify the ratio of influence in and out. A blue node indicates that the associated entity has influence the ego more than the ego has influenced itself. Likewise, a red node indicates the ego has influenced the node's entity more than it has influenced the ego.

<p align="center">
  <img src="https://github.com/csmetrics/influencemap/blob/master/assets/img/gradiant_key.png"/>
</p>

We define two entities to be coauthors if the entities have contributed to the same paper. Coauthors of the ego are signified by nodes with green borders and greyed out names.

## Data

We use the [microsoft academic graph (MAG)](https://www.microsoft.com/en-us/research/project/microsoft-academic-graph/) dataset for our visualization. The dataset is a large curation of publication indexed by Bing. From MAG, we use the following fields of the paper entries in the dataset,

- Citation links
- Authors
- Conferences
- Journals
- Author Affiliations

## Influence

To quantify academic influence, we define influence as a function of paper citations. Each citation which the ego is apart of contributes to the overall influence map of an ego. To prevent papers with a large number of entities contributing from creating an overwhelming amount of influence, we normalize the influence contribution by the number of entities in the cited paper.

<p align="center">
  <img src="https://github.com/csmetrics/influencemap/blob/master/assets/img/influence_weight.png"/>
</p>

For example, consider the following four paper database where we are only consider entities which are authors.

| Name         | Paper            | no. authors | cites papers                     |
|--------------|------------------|-------------|----------------------------------|
| John Smith   | Algorithms       | 2           | [Linear Algebra]                 |
| John Smith   | Machine Learning | 3           | [Linear Algebra, Computation]    |
| Maria Garcia | Linear Algebra   | 2           | None                             |
| Maria Garcia | Computation      | 4           | [Algorithms]                     |

In this case John's influence on Maria is 0.5 (John's paper Algorithm's has a weight of 0.5 and was cited once by Maria). 

On the other hand Maria's influence on John is 1.25 (Linear Algebra has a weight of 0.5 and it was cited twice by John, Computation has a weight of 0.25 and was cited once by John).

We aggregate the pairwise influence of entities associated with the papers of the ego to generate the nodes of a flower. Each flowers' outer nodes can be a collection of several types of entities. In our influence flower application, we present 3 different flower types:

1. Author outer nodes
2. Venue (conferences or journals) outer nodes
3. Author Affiliation outer nodes

#### Removing self-citations

We define a self-citation between papers and a cited paper as a relation
dependent on the ego. A paper citation is a self-citation if both papers
have the ego as an author.

#### Why not remove all coauthor papers instead?
 
When removing all coauthor papers (all scores from papers with a coauthor of
the referencing paper authors) we found the 'cut down' to be too extreme. This
would greatly effect the produced flower, leaving one with little to no
information.

#### Other candidate definitions of influence 

We have described influence as the sum of citations from one person (or venue or affiliation) to another, weighted by the number of authors in the citing paper. Similar methods were considered early on in the project which included combinations of different weighting schemes. We looked at the eight combinations of three mutually exclusive weightings:

1. Weighting by the number of authors on the citing paper;
2. Weighting by the number of authors on the cited paper; and
3. Weighting by the number of papers referenced by the citing paper.

Due to the lack of a ground truth value of influence to compare these definitions to, we evaluated the eight combinations of these weightings empirically by discussing with researchers which of the definitions produced flowers that most accurately reflected their opinions of who they have influenced and been influenced by.

Other definitions of influence which have not yet been explored with this data include existing measures for node centrality in graphs. By using citation data from MAG to define a directed graph where nodes represent authors, venues or affiliations, and edges are derived from citations between nodes, we could explore using metrics such as closeness, betweenness and eigenvector centrality. These metrics are more appropriate for defining the influence of an entity relative to the whole network.
