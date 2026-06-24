## 5 Known Issues & Feedback

The systems used for advising and university processes are not perfect. This section collects issues
we have found, and suggestions for improvement when possible.

### 5.1 S3/SIO

```
● Counting the 360 units for graduation in S3 is wrong. (E.g. StuCos and Courses repeated count
twice in the C vs. D grade)
● Grades are not processed at the right time
● It is super slow
```
### 5.2 Stellic

```
● Counting the 360 units for graduation in Stellic is wrong (number of courses and units does not
match those counted manually). Stellic added a "Degree Check" requirement for QCS students
as a workaround. It seems to work.
(We have a script in our github repo that does that for us. But there is still some inconsistency.)
● The double counting rule for the Computer Systems concentration cannot be easily implemented
on Stellic, so if a student is taking 5 courses towards that concentration, and needs to double
count two of them, we need to add the double counting manually.
● The Professional Writing Minor requirements on Stellic and on the document in Scotty do not
seem to be consistent. Please consult with the minor advisor for what courses may or may not
count for each student.
● Programs in Stellic (the cards that appear when one clicks on the "Programs" link on the left
menu) correspond to degrees in S3. Each program in Stellic might have different audits that apply
to different students (e.g. different entry years or campus), and such audits only exist on Stellic.
● The green checkmark next to a prerequisite in the right-side tab only means that the student has
passed the prerequisite; it does not mean that they also got a high enough grade to satisfy the
prerequisite. Here is an example: The tab for Concepts shows
and the min-grade constraints:
when the student has actually only gotten D in 21-120 and 21-108:
```

```
So, the checkmarks for 21-120 and 21-108 are not correct.
```
### 5.3 University Processes

```
● The process of declaring minors and concentrations by sending forms and emails to Jarrin seems
to be too complicated.
```
### 5.4 Program structure

Below is a list of remarks on the prerequisite structure of the CS major. We use “OFFICIAL” for the
official description of the program; “STELLIC” for the description of the Doha program in Stellic.
_First-year Immigration_ is listed as 07-128 in OFFICIAL, but 07-129 in STELLIC. Not sure why the
Doha program should use a different number.
○ Giselle: They had a different number of units until this year. I think 07-128 is now 3 units,
and its description is broad enough that we can use the 128 number instead. I will try to
make this change starting next year, since the schedule, registration, etc is already done
for 2023.
_Research and Innovation in Computer Science_ (for the _Technical Communication_ requirement):
○ In OFFICIAL, it is listed as 07-300 and has mild requirements (only English courses);
○ in STELLIC, it is listed as 15-300, and has much stronger requirements (76-101 and two
of the three courses 15-210, 15-213, 15-251).
_Two Computer Science Electives_ requirement: OFFICIAL contains the following vague clause:
“ _Some IDEATE courses and some SCS undergraduate and graduate courses might not be
allowed based on course content. Consult with a CS undergraduate advisor before registration to
determine eligibility for this requirement._ ” How do we get to know which is allowed?
_Science and Engineering_ requirement:
○ The two lists of exceptions (i.e., courses that cannot count towards this requirement), in
OFFICIAL and STELLIC, are different.
○ STELLIC has a very weird way of implementing the restriction that “at least two courses
should be from the same department”. It is unclear what it does, and whether it is correct.
In the requirement _Mathematics and Probability | Probability | Probability and Statistics_ : OFFICIAL
says you need two courses (36-225 and 36-226); but STELLIC says you need four courses
(36-225 and 36-226 and 36-235 and 36-236).
○ Mark says the correct expression is (36-225 and 36-226) OR (36-235 and 36-236) and
that this will be in OFFICIAL starting Fall 2023.
○ Jarrin will change STELLIC so that it uses this OR.
○ Still, the second disjunct should be replaced by just 36-236, because 36-235 is a
prerequisite of 36-236 anyway.
[ _Passed on to CRC (10MAR2025)_ ] The prerequisite for 15-151 _Mathematical Foundations for Computer
Science_ (i.e., the CS version of Concepts) is just 21-210 _Differential and Integral Calculus_. This is
in sharp contrast to 21-127 and 21-128 (the Math version of Concepts), where the prerequisite is
an OR of the following four courses: 21-210, 21-112, 21-108, 15-112. It looks reasonable to
change the prerequisites of 15-151 to be the same OR of all four courses.
15-151 _Mathematical Foundations for Computer Science_ is a prerequisite for _Programming
Languages_ concentration. This course is the SCS version of Concepts. So, this should change to
21-127 or 21-128 or 15-151 (numerous courses already recognize this interchangeability).
15-213 _Introduction to Computer Systems_ :
○ In OFFICIAL, it is required to be one of the core courses.
○ In STELLIC, it is required to be either this or 18-213.


If the correct choice is the latter, then perhaps all of the courses and programs which currently list
only 15-213 as prerequisite can replace that with 15-213 or 18-213 namely:
○ constrained electives for _Software Systems_
○ the _Computer Systems_ concentration as a whole
○ 15-316 _Software Foundations of Security & Privacy_
○ 15-330 _Introduction to Computer Security_
[ _Passed on to CRC (10MAR2025)_ ] _Matrix courses_ 21-240, 21-241, 21-242: There is too much variety on
which of these are enough preparation for other courses. It seems simpler & still correct to have
the OR of all three courses as the common prerequisite in all cases. Here is the current wild
variety:
○ 15-451 _Algorithm Design and Analysis_ lists only 241.
○ 11-485 _Introduction to Deep Learning_ lists only 241.
○ 15-281 _AI: Representation and Problem Solving_ lists 240 or 241.
○ The _Mathematics and Probability_ | _Matrix/Linear Algebra_ requirement lists 241 or 242.
○ 21-484 _Graph Theory_ lists 241 or 242.
○ Each of the courses 21-266, 21-268, 21-269 lists 241 or 242.
○ 10-315 _Introduction to Machine Learning_ lists 240 or 241 or 242.
17-313 _Foundations of Software Engineering_ : How come it has no prerequisites whatsoever?
Don’t you need to have some coding experience first?
○ _Ryan_ : _I think this is a historical thing. ISR (now S3D) didn't want to limit who could enroll as long as they have
sufficient programming experience from some source. They also strongly prefer experience (like an internship)
that they can't enforce with pre-reqs anyway. The assumption is that students without sufficient background
won't be silly enough to sign up. (Although I think some sort of pre-req would be helpful...)
The course webpage/syllabus says: There are no formal prerequisites, but we strongly recommend having a
solid foundation in programming before taking this class (e.g. 15-121, 15-122). You will also get more out of the
course if you have experience with some larger development projects, for example, through larger class
projects (e.g. 17-214, 15-410), internships, or open-source contributions. If you have questions, please don't
hesitate to reach out to the class instructors_.
[ _Passed on to CRC (10MAR2025)_ ] 15-251 _Great Ideas in Theoretical Computer Science_ and 21-228
_Discrete Mathematics_ : Many courses have the OR of these two as a prerequisite: 15-451,
15-312, 15-356, 21-301, 21-484. But 15-455 _Undergraduate Complexity Theory_ and _Algorithms
and Complexity_ concentration and _Programming Languages_ concentration all require only
15-251. This looks like an omission. They should probably all change this to 15-251 or 21-228.
15-281 _AI: Representation and Problem Solving_ : For _Artificial Intelligence_ requirement, STELLIC
lists both this course and a course 15-381 with the same title. But OFFICIAL lists only 15-281.
○ Giselle: This is because 15-381 became 15-281 after some point. The requirement for
15-318 still exists in Stellic to cover students that have taken this course number in the
past. But the 15-381 requirement should be removed eventually.
15-281 _AI: Representation and Problem Solving_ : In STELLIC, the matrix algebra capacity for this
course can also be covered by 18-202. In OFFICIAL, this course is not listed.
[ _Passed on to CRC (10MAR2025)_ ] It seems that 21-112 and 21-120 are interchangeable as prerequisites.
This is explicitly mentioned in the course description of 21-112 ( _“Successful completion of 21-111
and 21-112 entitles a student to enroll in any mathematics course for which 21-120 is a
prerequisite.”_ ) and is also used by several courses: 21-127, 21-128, 36-218, 21-122. But 11-485
_Introduction to Deep Learning_ lists only 21-120. This should probably change to 21-120 or
21-112.
15-459 _Undergraduate Quantum Computation_ is listed as elective for _Algorithms and Complexity_
concentration in OFFICIAL, but not in STELLIC.
[ _Passed on to CRC (10MAR2025)_ ] 36-218 Probability Theory for Computer Scientists: This is a 200-level
course which is listed as a prerequisite for _Algorithms and Complexity_ concentration. But then
none of the required or elective courses for that concentration have 36-218 as a prerequisite. This
is strange. A more natural structure would either have several of the other courses require it; or
have the course be completely removed from the prerequisites for the concentration.
The courses 15-346, 18-344, 18-447 are listed as electives for _Computer Systems_ concentration
in OFFICIAL, but not in STELLIC.
