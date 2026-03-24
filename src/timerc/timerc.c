#include <Python.h>
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif

#define LIST_START_CAPACITY 10
#define LIST_CAPACITY_MULT 2

typedef struct
{
    double start;
    double cooldown;
    PyObject *callback;
} Timer;

typedef struct
{
    Timer *timers;
    int len;
    int capacity;
} TimerList;

static TimerList *global_timers = NULL;

// C functions
static double get_time()
{
#ifdef _WIN32
    LARGE_INTEGER time, freq;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&time);
    return (double)time.QuadPart / (double)freq.QuadPart;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1000000000.0;
#endif
}

static TimerList *
allocate_list(int capacity)
{
    TimerList *list = (TimerList *)malloc(sizeof(TimerList));
    list->len = 0;
    list->capacity = capacity;
    list->timers = (Timer *)malloc(capacity * sizeof(Timer));
    return list;
}

static void
list_resize(TimerList *list)
{
    Timer *new_timers = (Timer *)malloc(list->capacity * LIST_CAPACITY_MULT * sizeof(Timer));
    memcpy(new_timers, list->timers, list->capacity * sizeof(Timer));
    free(list->timers);
    list->timers = new_timers;
    list->capacity = list->capacity * LIST_CAPACITY_MULT;
}

static void
list_add(TimerList *list, Timer timer)
{
    if (list->len >= list->capacity)
    {
        list_resize(list);
    }
    list->timers[list->len] = timer;
    list->len++;
}

static void
list_pop(TimerList *list, int i)
{
    Py_XDECREF(list->timers[i].callback);
    list->timers[i] = list->timers[list->len - 1];
    list->len--;
}

// Py functions
static PyObject *
timerc_add(PyObject *self, PyObject *args, PyObject *kwargs)
{
    double cooldown;
    PyObject *callback;

    char *const keywords[] = {"cooldown", "callback", NULL};
    if (PyArg_ParseTupleAndKeywords(args, kwargs, "dO", keywords, &cooldown, &callback) < 0)
    {
        return NULL;
    }

    Timer timer;
    timer.start = get_time();
    timer.cooldown = cooldown;
    timer.callback = callback;
    Py_XINCREF(callback);
    list_add(global_timers, timer);
    Py_RETURN_NONE;
}

static PyObject *
timerc_frame(PyObject *self, PyObject *null)
{
    int len = global_timers->len;
    double now = get_time();
    for (int i = 0; i < len; i++)
    {
        if ((now - global_timers->timers[i].start) >= global_timers->timers[i].cooldown)
        {
            if (global_timers->timers[i].callback != NULL)
            {
                PyObject *result = PyObject_CallNoArgs(global_timers->timers[i].callback);
                if (result == NULL)
                {
                    return NULL; // exception set
                }
                if (Py_IsNone(result))
                {
                    list_pop(global_timers, i);
                }
                else
                {
                    Py_XDECREF(global_timers->timers[i].callback);
                    global_timers->timers[i].start = now;
                    global_timers->timers[i].callback = result;
                }
            }
            else
            {
                list_pop(global_timers, i);
            }
        }
    }
    Py_RETURN_NONE;
}

static void timerc_free(void *module)
{
    if (global_timers != NULL)
    {
        if (global_timers->timers != NULL)
        {
            for (int i = 0; i < global_timers->len; i++)
            {
                Py_XDECREF(global_timers->timers[i].callback);
            }
            free(global_timers->timers);
        }
        free(global_timers);
        global_timers = NULL;
    }
}

static PyMethodDef timerc_methods[] = {
    {"frame", (PyCFunction)timerc_frame, METH_NOARGS, NULL},
    {"add", (PyCFunction)timerc_add, METH_VARARGS | METH_KEYWORDS, NULL},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef timerc_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "timerc",
    .m_doc = NULL, /* docs*/
    .m_size = -1,
    .m_methods = timerc_methods,
    .m_free = (freefunc)timerc_free};

PyMODINIT_FUNC PyInit_timerc(void)
{
    global_timers = allocate_list(LIST_START_CAPACITY);

    return PyModule_Create(&timerc_module);
}