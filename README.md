# project influencemap @ANU

Goal: Constructing maps of intellectual influence using academic data.

Make it searchable and visualisable on the web.

## methodologyit cites
The influence of a person, institution or conference (an entity) on and from other entities is measured using citations. The influence flowers show a normalised influence score meaning that flowers for two different entities cannot be directly compared. The underlying influence scores depend on the number of citations to and from an entity and the number of authors involved in the publications recieving the citations.
### calculating the influence one entity has on another entity
Influence on an entity is calculated as the sum of the per author weight for each of the citations to a paper written by that entity, as shown below.

![calculation of a's influence on b](https://github.com/csmetrics/influencemap/blob/master/assets/influence_calulation.png)

For example, consider the following four paper database.

| Name         | Paper            | no. authors | cites papers                     |
|--------------|------------------|-------------|----------------------------------|
| John Smith   | Algorithms       | 2           | [Linear Algebra]                 |
| John Smith   | Machine Learning | 3           | [Linear Algebra, Computation]    |
| Maria Garcia | Linear Algebra   | 2           | None                             |
| Maria Garcia | Computation      | 4           | [Algorithms]                     |

In this case John's influence on Maria is 0.5 (John's paper Algorithm's has a weight of 0.5 and was cited once by Maria). 

On the other hand Maria's influence on John is 1.25 (Linear Algebra has a weight of 0.5 and it was cited twice by John, Computation has a weight of 0.25 and was cited once by John).

### visualising the influence
To visualise the influence that one entity has on others, the influence scores are calculated as described above for the entity and each other entity that cites it. The scores of the most influential entities are normalised and used as weights for the graph's edges to show their relative influence. Similarly, visualising how one is influenced involves finding the scores for each entity that has influenced (been cited by) them and plotting the normalised scores as weights on a weighted graph.
