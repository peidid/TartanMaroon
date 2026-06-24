'use client';

import { useState, useEffect } from 'react';
import { X, Loader2, Save, Plus, Trash2, GraduationCap, BookOpen, Target } from 'lucide-react';
import { auth, UserProfile, CourseTaken } from '@/lib/api';

interface ProfileModalProps {
  profile?: UserProfile;
  onClose: () => void;
  onSave: (profile: UserProfile) => void;
}

// Common course names for autocomplete
const COURSE_NAMES: Record<string, string> = {
  '15-112': 'Fundamentals of Programming',
  '15-122': 'Principles of Imperative Computation',
  '15-150': 'Principles of Functional Programming',
  '15-213': 'Introduction to Computer Systems',
  '15-251': 'Great Ideas in Theoretical Computer Science',
  '15-410': 'Operating System Design',
  '21-127': 'Concepts of Mathematics',
  '21-241': 'Matrices and Linear Transformations',
  '67-262': 'Database Design and Development',
  '67-272': 'Application Design and Development',
  '67-373': 'Software Development Project',
  '76-101': 'Interpretation and Argument',
};

const GRADE_OPTIONS = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'R', 'P', 'N'];
const SEMESTER_OPTIONS = [
  'Fall 2023', 'Spring 2024', 'Summer 2024',
  'Fall 2024', 'Spring 2025', 'Summer 2025',
  'Fall 2025', 'Spring 2026', 'Summer 2026',
];

type TabType = 'academic' | 'courses' | 'goals';

export default function ProfileModal({ profile, onClose, onSave }: ProfileModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>('academic');

  // Academic Info
  const [major, setMajor] = useState(profile?.major || '');
  const [year, setYear] = useState(profile?.year || '');
  const [minors, setMinors] = useState(profile?.minors?.join(', ') || '');
  const [concentration, setConcentration] = useState(profile?.concentration || '');
  const [gpa, setGpa] = useState(profile?.gpa?.toString() || '');
  const [expectedGraduation, setExpectedGraduation] = useState(profile?.expected_graduation || '');

  // Courses
  const [coursesTaken, setCoursesTaken] = useState<CourseTaken[]>(
    profile?.courses_taken || []
  );
  const [newCourse, setNewCourse] = useState<CourseTaken>({
    code: '', grade: '', semester: '', name: ''
  });

  // Goals
  const [interests, setInterests] = useState(profile?.interests?.join(', ') || '');
  const [careerGoals, setCareerGoals] = useState(profile?.career_goals?.join('\n') || '');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Auto-fill course name when code is entered
  useEffect(() => {
    if (newCourse.code && COURSE_NAMES[newCourse.code]) {
      setNewCourse(prev => ({ ...prev, name: COURSE_NAMES[newCourse.code] }));
    }
  }, [newCourse.code]);

  const addCourse = () => {
    if (newCourse.code && newCourse.grade && newCourse.semester) {
      setCoursesTaken([...coursesTaken, { ...newCourse }]);
      setNewCourse({ code: '', grade: '', semester: '', name: '' });
    }
  };

  const removeCourse = (index: number) => {
    setCoursesTaken(coursesTaken.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const profileData: UserProfile = {
      major: major || undefined,
      year: year || undefined,
      minors: minors ? minors.split(',').map((s) => s.trim()).filter(Boolean) : [],
      concentration: concentration || undefined,
      gpa: gpa ? parseFloat(gpa) : undefined,
      expected_graduation: expectedGraduation || undefined,
      completed_courses: coursesTaken.map(c => c.code),
      courses_taken: coursesTaken,
      interests: interests ? interests.split(',').map((s) => s.trim()).filter(Boolean) : [],
      career_goals: careerGoals ? careerGoals.split('\n').map((s) => s.trim()).filter(Boolean) : [],
    };

    try {
      await auth.updateProfile(profileData);
      onSave(profileData);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'academic' as TabType, label: 'Academic Info', icon: GraduationCap },
    { id: 'courses' as TabType, label: 'Courses Taken', icon: BookOpen },
    { id: 'goals' as TabType, label: 'Goals', icon: Target },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl w-full max-w-2xl mx-4 overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="bg-cmu-red text-white p-6 relative flex-shrink-0">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1 hover:bg-white/20 rounded"
          >
            <X className="w-5 h-5" />
          </button>
          <h2 className="text-2xl font-bold">Academic Profile</h2>
          <p className="text-white/80 mt-1">
            Help us personalize your advising experience
          </p>
        </div>

        {/* Tabs */}
        <div className="flex border-b bg-gray-50 flex-shrink-0">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-cmu-red border-b-2 border-cmu-red bg-white'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto flex-1">
          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          {/* Academic Info Tab */}
          {activeTab === 'academic' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Primary Major
                  </label>
                  <select
                    value={major}
                    onChange={(e) => setMajor(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
                  >
                    <option value="">Select major</option>
                    <option value="Information Systems">Information Systems</option>
                    <option value="Computer Science">Computer Science</option>
                    <option value="Business Administration">Business Administration</option>
                    <option value="Biological Sciences">Biological Sciences</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Academic Year
                  </label>
                  <select
                    value={year}
                    onChange={(e) => setYear(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
                  >
                    <option value="">Select year</option>
                    <option value="First Year">First Year</option>
                    <option value="Sophomore">Sophomore</option>
                    <option value="Junior">Junior</option>
                    <option value="Senior">Senior</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Concentration
                  </label>
                  <input
                    type="text"
                    value={concentration}
                    onChange={(e) => setConcentration(e.target.value)}
                    placeholder="e.g., AI/ML, Systems"
                    className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Expected Graduation
                  </label>
                  <select
                    value={expectedGraduation}
                    onChange={(e) => setExpectedGraduation(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
                  >
                    <option value="">Select semester</option>
                    <option value="Spring 2025">Spring 2025</option>
                    <option value="Fall 2025">Fall 2025</option>
                    <option value="Spring 2026">Spring 2026</option>
                    <option value="Fall 2026">Fall 2026</option>
                    <option value="Spring 2027">Spring 2027</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Current GPA
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="4"
                    value={gpa}
                    onChange={(e) => setGpa(e.target.value)}
                    placeholder="e.g., 3.5"
                    className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Minors (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={minors}
                    onChange={(e) => setMinors(e.target.value)}
                    placeholder="e.g., Math, Data Science"
                    className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Courses Tab */}
          {activeTab === 'courses' && (
            <div className="space-y-4">
              {/* Add Course Form */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Add a Course</h3>
                <div className="grid grid-cols-12 gap-2">
                  <div className="col-span-3">
                    <input
                      type="text"
                      value={newCourse.code}
                      onChange={(e) => setNewCourse({ ...newCourse, code: e.target.value.toUpperCase() })}
                      placeholder="15-112"
                      className="w-full px-3 py-2 border rounded-lg text-sm focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
                    />
                  </div>
                  <div className="col-span-3">
                    <select
                      value={newCourse.grade}
                      onChange={(e) => setNewCourse({ ...newCourse, grade: e.target.value })}
                      className="w-full px-3 py-2 border rounded-lg text-sm focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
                    >
                      <option value="">Grade</option>
                      {GRADE_OPTIONS.map(g => (
                        <option key={g} value={g}>{g}</option>
                      ))}
                    </select>
                  </div>
                  <div className="col-span-4">
                    <select
                      value={newCourse.semester}
                      onChange={(e) => setNewCourse({ ...newCourse, semester: e.target.value })}
                      className="w-full px-3 py-2 border rounded-lg text-sm focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
                    >
                      <option value="">Semester</option>
                      {SEMESTER_OPTIONS.map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                  <div className="col-span-2">
                    <button
                      type="button"
                      onClick={addCourse}
                      disabled={!newCourse.code || !newCourse.grade || !newCourse.semester}
                      className="w-full h-full bg-cmu-red text-white rounded-lg hover:bg-cmu-darkred transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                {newCourse.name && (
                  <p className="text-xs text-gray-500 mt-1">{newCourse.name}</p>
                )}
              </div>

              {/* Course List */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">
                  Courses Taken ({coursesTaken.length})
                </h3>
                {coursesTaken.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-4">
                    No courses added yet. Add your completed courses above.
                  </p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {coursesTaken.map((course, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between bg-white border rounded-lg px-3 py-2"
                      >
                        <div className="flex items-center gap-3">
                          <span className="font-mono font-medium text-cmu-red">
                            {course.code}
                          </span>
                          <span className="text-gray-600 text-sm">
                            {course.name || COURSE_NAMES[course.code] || ''}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-sm bg-gray-100 px-2 py-0.5 rounded">
                            {course.grade}
                          </span>
                          <span className="text-sm text-gray-500">
                            {course.semester}
                          </span>
                          <button
                            type="button"
                            onClick={() => removeCourse(index)}
                            className="text-gray-400 hover:text-red-500 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Goals Tab */}
          {activeTab === 'goals' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Career Interests (comma-separated)
                </label>
                <input
                  type="text"
                  value={interests}
                  onChange={(e) => setInterests(e.target.value)}
                  placeholder="e.g., Software Engineering, Data Science, Product Management"
                  className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Career Goals (one per line)
                </label>
                <textarea
                  value={careerGoals}
                  onChange={(e) => setCareerGoals(e.target.value)}
                  placeholder="e.g.,&#10;Work at a tech company as a software engineer&#10;Pursue graduate studies in AI&#10;Start my own startup"
                  rows={5}
                  className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none resize-none"
                />
              </div>

              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-blue-700">
                  <strong>Tip:</strong> The more specific you are about your goals,
                  the better we can tailor course recommendations and academic planning
                  to help you achieve them.
                </p>
              </div>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="border-t p-4 bg-gray-50 flex-shrink-0">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full bg-cmu-red text-white py-3 rounded-lg font-medium hover:bg-cmu-darkred transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Profile
          </button>
        </div>
      </div>
    </div>
  );
}
