# PARCI

A PARtial Continuous Integration tool

## Description
This is a mini CI system where you write a "taskfile" which defines various "tasks" which
are specified to be executed in a specific order and which provides a variety of conveniences
around running commands, containers, and storing/retrieving parameters in a variety of reasonably
secure ways.

Think of it like Jenkinsfiles meet Airflow DAGs but without all the infrastructure.

Parci can be executed from inside of Jenkinsfiles or as part of Airflow DAGs (or, really, anything
else you might want to use it within since you can easily run tasks on the command line) but
is meant primarily to make local development faster while automatically cleaning up the kinds of
messes that CI systems tend to leave around.
