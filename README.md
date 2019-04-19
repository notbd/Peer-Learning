# Peer-Learning

*A web application that allows students to group up with other users in the same class and collaboratively tackle problems posted by the instructor.*

##### *Home Page Screenshot:*
![image](https://user-images.githubusercontent.com/25305842/56397983-10a6b080-620c-11e9-92b0-c7654c225a8d.png)

##### *Instructor Panel Screenshot:*
![image](https://user-images.githubusercontent.com/25305842/56398289-3e402980-620d-11e9-9cd0-a70c6b3efccc.png)

##### *Student Answer Page Screenshot:*
![image](https://user-images.githubusercontent.com/25305842/56398290-3e402980-620d-11e9-80e7-75ac58a7a74e.png)

##### *Profile Page Screenshot:*
![image](https://user-images.githubusercontent.com/25305842/56397982-10a6b080-620c-11e9-8a2d-b60668a9935e.png)



## DEPLOY

### clone repo:
``` bash

git clone git@github.com:zhang13music/Peer-Learning.git
cd Peer-Learning

```
### install dependencies (ideally within virtual environment):
``` bash

pip install -r requirement.txt

```
### init database:
``` bash

python db_create.py

```
### run flask application:
``` bash

python application.py

```
> NOTE: Make sure the python version under using is `Python 2`.
