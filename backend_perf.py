import psycopg2
import psycopg2.extras
import json

class DatabaseManager:
    """Manages all database operations for the Performance Management System."""
    
    def __init__(self, db_name, user, password, host, port):
        """Initializes the database connection."""
        self.conn_params = {
            'dbname': 'PMS System',
            'user': 'postgres',
            'password': 'bijujohn',
            'host': 'localhost',
            'port': '5432'
        }

    def _get_connection(self):
        """Creates and returns a new database connection."""
        return psycopg2.connect(**self.conn_params)

    def _execute_query(self, query, params=None, fetch=False):
        """A helper to execute a query with optional parameters and fetching results."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    return cur.fetchall()
                conn.commit()

    def create_tables(self):
        """Creates all necessary tables. Assumes they don't exist."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Drop tables in a safe order due to foreign key constraints
                    cur.execute("""
                        DROP TABLE IF EXISTS employee_skills CASCADE;
                        DROP TABLE IF EXISTS employee_certifications CASCADE;
                        DROP TABLE IF EXISTS client_requirements CASCADE;
                        DROP TABLE IF EXISTS certifications CASCADE;
                        DROP TABLE IF EXISTS skills CASCADE;
                        DROP TABLE IF EXISTS employees CASCADE;
                        DROP TABLE IF EXISTS clients CASCADE;
                    """)
                    conn.commit()
                    
                    # Create tables
                    cur.execute("""
                        CREATE TABLE employees (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            role VARCHAR(255),
                            experience_years INTEGER,
                            performance_score INTEGER DEFAULT 0
                        );
                        CREATE TABLE skills (
                            id SERIAL PRIMARY KEY,
                            skill_name VARCHAR(255) UNIQUE NOT NULL
                        );
                        CREATE TABLE certifications (
                            id SERIAL PRIMARY KEY,
                            certification_name VARCHAR(255) UNIQUE NOT NULL
                        );
                        CREATE TABLE clients (
                            id SERIAL PRIMARY KEY,
                            client_name VARCHAR(255) UNIQUE NOT NULL
                        );
                        CREATE TABLE employee_skills (
                            employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
                            skill_id INTEGER REFERENCES skills(id) ON DELETE CASCADE,
                            PRIMARY KEY (employee_id, skill_id)
                        );
                        CREATE TABLE employee_certifications (
                            employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
                            certification_id INTEGER REFERENCES certifications(id) ON DELETE CASCADE,
                            PRIMARY KEY (employee_id, certification_id)
                        );
                        CREATE TABLE client_requirements (
                            id SERIAL PRIMARY KEY,
                            client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
                            skill_id INTEGER REFERENCES skills(id) ON DELETE CASCADE,
                            certification_id INTEGER REFERENCES certifications(id) ON DELETE CASCADE
                        );
                    """)
                    conn.commit()
        except psycopg2.OperationalError as e:
            raise e

    def add_employee(self, name, role, experience, score):
        """Adds a new employee to the database."""
        self._execute_query("INSERT INTO employees (name, role, experience_years, performance_score) VALUES (%s, %s, %s, %s)", (name, role, experience, score))

    def add_client(self, client_name):
        """Adds a new client to the database."""
        self._execute_query("INSERT INTO clients (client_name) VALUES (%s)", (client_name,))

    def add_skill(self, skill_name):
        """Adds a new skill to the database."""
        self._execute_query("INSERT INTO skills (skill_name) VALUES (%s) ON CONFLICT (skill_name) DO NOTHING", (skill_name,))

    def add_certification(self, cert_name):
        """Adds a new certification to the database."""
        self._execute_query("INSERT INTO certifications (certification_name) VALUES (%s) ON CONFLICT (certification_name) DO NOTHING", (cert_name,))

    def assign_skill_to_employee(self, employee_id, skill_id):
        """Links a skill to an employee."""
        self._execute_query("INSERT INTO employee_skills (employee_id, skill_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (employee_id, skill_id))

    def assign_cert_to_employee(self, employee_id, cert_id):
        """Links a certification to an employee."""
        self._execute_query("INSERT INTO employee_certifications (employee_id, certification_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (employee_id, cert_id))
    
    def assign_requirements_to_client(self, client_id, skill_ids, cert_ids):
        """Assigns skill and cert requirements to a client."""
        # Clear existing requirements first
        self._execute_query("DELETE FROM client_requirements WHERE client_id = %s", (client_id,))
        
        # Add new requirements
        for skill_id in skill_ids:
            self._execute_query("INSERT INTO client_requirements (client_id, skill_id, certification_id) VALUES (%s, %s, NULL)", (client_id, skill_id))
        for cert_id in cert_ids:
            self._execute_query("INSERT INTO client_requirements (client_id, skill_id, certification_id) VALUES (%s, NULL, %s)", (client_id, cert_id))

    def get_all_employees(self):
        """Retrieves all employees."""
        return self._execute_query("SELECT id, name, role, experience_years, performance_score FROM employees ORDER BY id", fetch=True)

    def get_all_clients(self):
        """Retrieves all clients."""
        return self._execute_query("SELECT id, client_name FROM clients ORDER BY id", fetch=True)

    def get_all_skills(self):
        """Retrieves all skills."""
        return self._execute_query("SELECT id, skill_name FROM skills ORDER BY id", fetch=True)

    def get_all_certifications(self):
        """Retrieves all certifications."""
        return self._execute_query("SELECT id, certification_name FROM certifications ORDER BY id", fetch=True)

    def find_best_agent(self, client_id):
        """Finds and ranks the best agents for a given client."""
        query = """
        SELECT
            e.id,
            e.name AS employee_name,
            e.role,
            e.experience_years,
            e.performance_score,
            ARRAY_AGG(DISTINCT s.skill_name) FILTER (WHERE s.skill_name IS NOT NULL) AS matched_skills,
            ARRAY_AGG(DISTINCT c.certification_name) FILTER (WHERE c.certification_name IS NOT NULL) AS matched_certifications,
            (COUNT(DISTINCT es.skill_id) * 10 + COUNT(DISTINCT ec.certification_id) * 20) AS match_score
        FROM
            employees AS e
        LEFT JOIN
            employee_skills AS es ON e.id = es.employee_id
        LEFT JOIN
            employee_certifications AS ec ON e.id = ec.employee_id
        LEFT JOIN
            skills AS s ON es.skill_id = s.id
        LEFT JOIN
            certifications AS c ON ec.certification_id = c.id
        LEFT JOIN
            client_requirements AS cr ON (cr.skill_id = s.id OR cr.certification_id = c.id)
        WHERE
            cr.client_id = %s
        GROUP BY
            e.id
        ORDER BY
            match_score DESC,
            e.performance_score DESC,
            e.experience_years DESC;
        """
        results = self._execute_query(query, (client_id,), fetch=True)
        return results
