const express = require('express');
const { Sequelize } = require('sequelize');
const config = require('config');
const authRoutes = require('./routes/authRoutes');

const app = express();
app.use(express.json());

const dbConfig = config.get('db');
const sequelize = new Sequelize(dbConfig.database, dbConfig.user, dbConfig.password, {
  host: dbConfig.host,
  dialect: 'postgres'
});

sequelize.authenticate()
  .then(() => console.log('Database connected...'))
  .catch(err => console.error('Unable to connect to the database:', err));

app.use('/api/auth', authRoutes);

const port = process.env.PORT || 4000;
app.listen(port, () => console.log(Server running on port ${port}));
