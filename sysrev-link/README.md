# Sysrev-Link
A script `popgraphdb.py` for taking a project id and building an srvc-neo4j graph.
This isn't meant to be an srvc-neo4j service, but I wasn't sure where to put it. 

To use this:

1. host a copy of the sysrev database at localhost:5470
2. run srvc-neo4j by running `docker-compose up` in the srvc-neo4j directory
3. run `popgraphdb.py` line by line. 

This isn't complete it's just a proof of concept. It's a good place to start for building individual services
because it gives you the schema from sysrev and some real world data.

Also, eventually we'll want to actually create srvc projects for each sysrev.

## TODO
1. Persist files:   
    I'm not sure 
