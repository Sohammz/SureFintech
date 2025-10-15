import React, { useState } from 'react';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
      setData(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a PDF file');
      return;
    }

    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('https://surefintechproject.onrender.com', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to parse statement');
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      setError('Error parsing PDF. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = () => {
    setFile(null);
    setData(null);
    setError('');
    const fileInput = document.querySelector('.file-input');
    if (fileInput) {
      fileInput.value = '';
    }
  };

  return (
    <div className="app">
      <div className="container">
        <h1> Credit Card Statement Parser</h1>
        <p>Upload your credit card statement PDF to extract key information</p>
        
        <div className="upload-section">
          <form onSubmit={handleSubmit}>
            <div className="file-input-wrapper">
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="file-input"
              />
              <label className="file-label">
                {file ? file.name : 'Choose PDF Statement'}
              </label>
            </div>
            
            <div className="button-group">
              <button 
                type="submit" 
                disabled={!file || loading}
                className="submit-btn"
              >
                {loading ? 'Processing...' : 'Extract Data'}
              </button>
              
              {file && (
                <button 
                  type="button" 
                  onClick={handleDelete}
                  className="delete-btn"
                >
                  Delete File
                </button>
              )}
            </div>
          </form>
        </div>

        {error && <div className="error">{error}</div>}

        {data && (
          <div className="results-section">
            <div className="results-header">
              <h2>Extracted Information</h2>

            </div>
            <div className="data-grid">
              <div className="data-item">
                <label>Card Issuer</label>
                <span>{data.cardIssuer}</span>
              </div>
              <div className="data-item">
                <label>Card Number</label>
                <span>**** {data.cardLastFour}</span>
              </div>
              <div className="data-item">
                <label>Card Variant</label>
                <span>{data.cardVariant}</span>
              </div>
              <div className="data-item">
                <label>Statement Date</label>
                <span>{data.statementDate}</span>
              </div>
              <div className="data-item">
                <label>Due Date</label>
                <span>{data.dueDate}</span>
              </div>
              <div className="data-item">
                <label>Total Amount Due</label>
                <span className="amount">₹{data.totalAmountDue}</span>
              </div>
            </div>
          </div>
        )}

        <div className="supported-cards">
          <h3>Supported Card Issuers</h3>
          <ul>
            <li>ICICI Bank</li>
            <li>HDFC Bank</li>
            <li>Axis Bank</li>
            <li>SBI Bank</li>
            <li>Kotak Bank</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default App;